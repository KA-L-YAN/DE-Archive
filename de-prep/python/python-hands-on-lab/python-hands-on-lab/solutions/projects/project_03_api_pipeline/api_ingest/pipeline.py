"""End-to-end API ingestion: extract (3 pagination styles) → validate → normalize → dedupe → enrich → write."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from . import sources, transform
from .client import ApiClient

log = logging.getLogger("api_ingest")


def write_jsonl_atomic(path: str | Path, records) -> int:
    """[provided] Write records as JSON Lines atomically. Returns the record count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    n = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
                n += 1
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return n


def load_state(path: str | Path) -> dict:
    """Read pipeline state ({"events_watermark": str}); missing file -> {"events_watermark": ""}."""
    path = Path(path)
    if not path.exists():
        return {"events_watermark": ""}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: str | Path, state: dict) -> None:
    """Persist state atomically (temp file + os.replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def run(session, base_url: str, output_dir: str | Path, state_path: str | Path, page_size: int = 100,
        sleep=time.sleep, max_attempts: int = 4) -> dict:
    """Ingest customers, orders and new events; return (and write) a summary.

    Outputs in output_dir:
      customers.jsonl, orders.jsonl          full snapshots, overwritten each run (idempotent)
      rejects.jsonl                          {"entity", "record", "errors"} for invalid records
      events/dt=YYYY-MM-DD/events-<watermark>.jsonl   only the *new* events of this run, by updated_at date
      summary.json
    The events watermark in state_path is saved only after all outputs are written.
    """
    out = Path(output_dir)
    client = ApiClient(session, base_url, max_attempts=max_attempts, sleep=sleep)
    state = load_state(state_path)
    started = time.perf_counter()
    rejects = []

    raw_customers = list(sources.iter_customers(client, page_size))
    good_customers = []
    for c in raw_customers:
        errors = transform.validate_customer(c)
        if errors:
            rejects.append({"entity": "customer", "record": c, "errors": errors})
        else:
            good_customers.append(transform.normalize_customer(c))
    customers, customer_dupes = transform.latest_by(good_customers, "customer_id", "customer_id")
    by_id = {c["customer_id"]: c for c in customers}

    raw_orders = list(sources.iter_orders(client, page_size))
    good_orders = []
    for o in raw_orders:
        errors = transform.validate_order(o)
        if errors:
            rejects.append({"entity": "order", "record": o, "errors": errors})
        else:
            good_orders.append(transform.normalize_order(o))
    orders, order_dupes = transform.latest_by(good_orders, "order_id", "updated_at")
    orders = transform.enrich_orders(orders, by_id)

    events, new_watermark = sources.fetch_events(client, state.get("events_watermark", ""), page_size)

    write_jsonl_atomic(out / "customers.jsonl", customers)
    write_jsonl_atomic(out / "orders.jsonl", orders)
    write_jsonl_atomic(out / "rejects.jsonl", rejects)
    by_day = defaultdict(list)
    for e in events:
        by_day[e["updated_at"][:10]].append(e)
    tag = new_watermark.replace(":", "").replace("-", "")
    for day, day_events in sorted(by_day.items()):
        write_jsonl_atomic(out / "events" / f"dt={day}" / f"events-{tag}.jsonl", day_events)

    summary = {
        "customers": {"fetched": len(raw_customers), "valid": len(good_customers), "unique": len(customers), "duplicates": customer_dupes},
        "orders": {"fetched": len(raw_orders), "valid": len(good_orders), "unique": len(orders), "duplicates": order_dupes,
                   "unknown_customer": sum(1 for o in orders if not o["customer_known"])},
        "events": {"new": len(events), "previous_watermark": state.get("events_watermark", ""), "watermark": new_watermark},
        "rejects": len(rejects), "http": dict(client.metrics), "duration_seconds": round(time.perf_counter() - started, 3),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_state(state_path, {**state, "events_watermark": new_watermark})
    log.info("ingested %d customers, %d orders, %d new events (%d rejects)", len(customers), len(orders), len(events), len(rejects))
    return summary
