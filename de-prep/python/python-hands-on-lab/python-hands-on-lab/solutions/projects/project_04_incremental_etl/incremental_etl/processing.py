"""Discovery, parsing/validation and change detection — no state mutation here."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

STATUSES = {"PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}


@dataclass(frozen=True)
class InputFile:
    key: str            # relative POSIX path, e.g. "dt=2026-01-01/orders_20260101_part1.csv"
    path: Path
    partition: str      # the dt value
    sha256: str
    size: int


def sha256_file(path: str | Path) -> str:
    """[provided] Chunked SHA-256."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def discover(input_dir: str | Path) -> list[InputFile]:
    """All `dt=*/**.csv` files under input_dir, sorted by (partition, key). Hidden/temp files ignored."""
    root = Path(input_dir)
    found = []
    for part_dir in sorted(p for p in root.glob("dt=*") if p.is_dir()):
        partition = part_dir.name.split("=", 1)[1]
        for f in sorted(part_dir.rglob("*.csv")):
            if f.name.startswith((".", "_")):
                continue
            found.append(InputFile(f.relative_to(root).as_posix(), f, partition, sha256_file(f), f.stat().st_size))
    return found


def classify(files: Iterable[InputFile], processed: dict[str, dict], processed_hashes: dict[str, str]) -> dict[str, list[InputFile]]:
    """Split files into new / changed / unchanged / redelivered.

    unchanged:   same key, same sha256 as already processed
    changed:     same key, different sha256 (corrected file)
    redelivered: new key, but content identical to an already processed file
    new:         everything else
    A redelivery inside the same batch (two new keys with identical content) counts the first as new.
    """
    result = {"new": [], "changed": [], "unchanged": [], "redelivered": []}
    seen_in_batch: set[str] = set()
    for f in files:
        entry = processed.get(f.key)
        if entry is not None:
            result["unchanged" if entry["sha256"] == f.sha256 else "changed"].append(f)
        elif f.sha256 in processed_hashes or f.sha256 in seen_in_batch:
            result["redelivered"].append(f)
        else:
            result["new"].append(f)
        seen_in_batch.add(f.sha256)
    return result


def _ts(value: str, field: str) -> datetime:
    """ISO string -> aware UTC datetime; ValueError mentioning `field` if invalid."""
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).astimezone(timezone.utc)
    except (AttributeError, ValueError):
        raise ValueError(f"{field} is not an ISO timestamp") from None


def validate(raw: dict) -> dict:
    """Typed order or ValueError. Timestamps are kept as canonical 'YYYY-MM-DDTHH:MM:SSZ' strings."""
    for field in ("order_id", "customer_id", "product_id"):
        if not (raw.get(field) or "").strip():
            raise ValueError(f"{field} is required")
    try:
        quantity, price = int(raw["quantity"]), float(raw["unit_price"])
    except (KeyError, ValueError):
        raise ValueError("quantity/unit_price not numeric") from None
    if quantity < 1 or price < 0:
        raise ValueError("quantity must be >= 1 and unit_price >= 0")
    status = (raw.get("status") or "").strip().upper()
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    order_ts, updated_at = _ts(raw.get("order_ts"), "order_ts"), _ts(raw.get("updated_at"), "updated_at")
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return {"order_id": raw["order_id"].strip(), "customer_id": raw["customer_id"].strip(), "product_id": raw["product_id"].strip(),
            "quantity": quantity, "unit_price": price, "amount": round(quantity * price, 2), "status": status,
            "order_ts": order_ts.strftime(fmt), "order_date": order_ts.date().isoformat(), "updated_at": updated_at.strftime(fmt),
            "channel": (raw.get("channel") or "").lower(), "country": (raw.get("country") or "").upper()}


def parse_file(f: InputFile) -> tuple[list[dict], list[dict]]:
    """Read + validate one file. Returns (valid records, rejects with `_error`, `_source`, `_line`)."""
    valid, rejects = [], []
    with f.path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            try:
                valid.append({**validate(raw), "_source": f.key})
            except ValueError as exc:
                rejects.append({**raw, "_error": str(exc), "_source": f.key, "_line": reader.line_num})
    return valid, rejects


def select_changes(records: Iterable[dict], order_index: dict[str, str]) -> tuple[list[dict], int]:
    """Keep only records newer than what's already loaded (and the newest within the batch).

    Returns (records to upsert — one per order_id, sorted by order_id, stale_or_duplicate_count).
    """
    best: dict[str, dict] = {}
    skipped = 0
    for r in records:
        known = order_index.get(r["order_id"])
        if known is not None and r["updated_at"] <= known:
            skipped += 1
            continue
        current = best.get(r["order_id"])
        if current is not None:
            skipped += 1
            if current["updated_at"] >= r["updated_at"]:
                continue
        best[r["order_id"]] = r
    return [best[k] for k in sorted(best)], skipped
