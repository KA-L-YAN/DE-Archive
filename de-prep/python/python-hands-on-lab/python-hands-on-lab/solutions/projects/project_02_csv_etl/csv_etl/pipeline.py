"""Orchestration: discover → read → validate → transform → dedupe → aggregate → write → audit."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import io, rules
from .config import Config

log = logging.getLogger("csv_etl")

CLEAN_FIELDS = ["order_id", "customer_id", "product_id", "quantity", "unit_price", "amount", "order_ts", "order_date",
                "status", "updated_at", "channel", "country", "customer_segment", "is_known_customer", "_source", "_line"]
REJECT_FIELDS = ["_source", "_line", "_error_field", "_error", "raw"]


class RejectThresholdExceeded(RuntimeError):
    """Too many rows were rejected; the audit report is attached as `.audit`."""

    def __init__(self, audit: dict):
        """[provided]"""
        super().__init__(f"reject ratio {audit['totals']['reject_ratio']:.2%} exceeds limit")
        self.audit = audit


def _iso(dt: datetime) -> str:
    """Aware datetime -> 'YYYY-MM-DDTHH:MM:SSZ'."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def run(config: Config, run_id: str | None = None, clock=time.perf_counter) -> dict:
    """Run the pipeline and return the audit dict (also written to output_dir/audit.json).

    Outputs (all written atomically):
      clean_orders.csv, daily_summary.csv, customer_summary.csv — only when the reject ratio is within limits
      rejected_rows.csv, audit.json — always
    Raises RejectThresholdExceeded (after writing rejects + audit) when the ratio is too high.
    """
    run_id = run_id or uuid.uuid4().hex[:12]
    started = datetime.now(timezone.utc)
    t0 = clock()
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    customers = io.load_customers(Path(config.input_dir) / config.customers_file if config.customers_file else None)

    files, valid, rejects = [], [], []
    for path in io.discover_files(config.input_dir, config.pattern):
        stats = {"file": path.name, "sha256": io.sha256_file(path), "rows_read": 0, "valid": 0, "rejected": 0}
        for raw in io.read_rows(path):
            stats["rows_read"] += 1
            try:
                record = rules.validate_row(raw, config.required_columns, config.allowed_status)
            except rules.ValidationError as exc:
                stats["rejected"] += 1
                payload = raw.get("_raw") or {k: v for k, v in raw.items() if not k.startswith("_")}
                rejects.append({"_source": raw["_source"], "_line": raw["_line"], "_error_field": exc.field, "_error": str(exc),
                                "raw": json.dumps(payload, ensure_ascii=False)})
                continue
            stats["valid"] += 1
            valid.append(rules.transform(record, customers))
        files.append(stats)
        log.info("read %s: %d rows, %d valid, %d rejected", path.name, stats["rows_read"], stats["valid"], stats["rejected"])

    deduped, duplicates = rules.dedupe_latest(valid, config.key, config.version_column)
    rows_read = sum(f["rows_read"] for f in files)
    reject_ratio = round(len(rejects) / rows_read, 4) if rows_read else 0.0
    outputs = [io.write_csv_atomic(out / "rejected_rows.csv", rejects, REJECT_FIELDS)]
    status = "SUCCEEDED" if reject_ratio <= config.max_reject_ratio else "FAILED"
    if status == "SUCCEEDED":
        clean_rows = ({**r, "order_ts": _iso(r["order_ts"]), "updated_at": _iso(r["updated_at"])} for r in deduped)
        outputs.append(io.write_csv_atomic(out / "clean_orders.csv", clean_rows, CLEAN_FIELDS))
        daily = rules.daily_summary(deduped)
        outputs.append(io.write_csv_atomic(out / "daily_summary.csv", daily, ["order_date", "country", "channel", "orders", "units", "revenue"]))
        outputs.append(io.write_csv_atomic(out / "customer_summary.csv", rules.customer_summary(deduped),
                                           ["customer_id", "segment", "orders", "revenue", "first_order", "last_order"]))
    reject_reasons: dict[str, int] = {}
    for r in rejects:
        reject_reasons[r["_error_field"]] = reject_reasons.get(r["_error_field"], 0) + 1
    audit = {
        "run_id": run_id, "status": status, "started_at": _iso(started), "duration_seconds": round(clock() - t0, 3),
        "config": {"input_dir": str(config.input_dir), "output_dir": str(config.output_dir), "pattern": config.pattern,
                   "max_reject_ratio": config.max_reject_ratio},
        "files": files,
        "totals": {"files": len(files), "rows_read": rows_read, "valid": len(valid), "rejected": len(rejects),
                   "duplicates_removed": duplicates, "unique_orders": len(deduped), "reject_ratio": reject_ratio,
                   "unknown_customers": sum(1 for r in deduped if not r["is_known_customer"])},
        "reject_reasons": dict(sorted(reject_reasons.items(), key=lambda kv: (-kv[1], kv[0]))),
        "outputs": [{"name": Path(o["path"]).name, "rows": o["rows"], "sha256": o["sha256"]} for o in outputs],
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    log.info("run %s %s: %d read, %d rejected, %d duplicates, %d unique", run_id, status, rows_read, len(rejects), duplicates, len(deduped))
    if status == "FAILED":
        raise RejectThresholdExceeded(audit)
    return audit
