"""A tiny file-based 'warehouse': a current-state orders table partitioned by order_date + a quarantine area."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable


class Warehouse:
    """Layout:
        <root>/orders/order_date=YYYY-MM-DD/part-00000.jsonl     current version of every order (sorted by order_id)
        <root>/quarantine/<run_id>/<source key with / -> __>.jsonl   rejected rows
    """

    def __init__(self, root: str | Path):
        """Remember root, orders_dir (<root>/orders) and quarantine_dir (<root>/quarantine)."""
        self.root = Path(root)
        self.orders_dir = self.root / "orders"
        self.quarantine_dir = self.root / "quarantine"

    def _partition_file(self, order_date: str) -> Path:
        """Path of the single part file for an order_date partition."""
        return self.orders_dir / f"order_date={order_date}" / "part-00000.jsonl"

    def load_partition(self, order_date: str) -> dict[str, dict]:
        """order_id -> row for one partition ({} if absent)."""
        path = self._partition_file(order_date)
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            return {row["order_id"]: row for row in map(json.loads, f)}

    def _write_partition(self, order_date: str, rows: dict[str, dict]) -> None:
        """Atomically write rows (sorted by order_id) to the partition file."""
        target = self._partition_file(order_date)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for oid in sorted(rows):
                    f.write(json.dumps(rows[oid], sort_keys=True) + "\n")
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def upsert(self, records: Iterable[dict]) -> dict[str, int]:
        """Merge records into their order_date partitions, rewriting each affected partition atomically.

        Returns {order_date: rows_written_into_it}. Records must already be the winning versions.
        """
        by_date: dict[str, list[dict]] = defaultdict(list)
        for r in records:
            by_date[r["order_date"]].append(r)
        touched = {}
        for order_date, rows in sorted(by_date.items()):
            current = self.load_partition(order_date)
            for r in rows:
                current[r["order_id"]] = {k: v for k, v in r.items() if k != "_line"}
            self._write_partition(order_date, current)
            touched[order_date] = len(rows)
        return touched

    def quarantine(self, rejects: list[dict], run_id: str, source_key: str) -> Path | None:
        """Write rejected rows for one source file; returns the path (None when there are no rejects)."""
        if not rejects:
            return None
        path = self.quarantine_dir / run_id / (source_key.replace("/", "__") + ".jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rejects), encoding="utf-8")
        return path

    def all_orders(self) -> dict[str, dict]:
        """Every current order across partitions."""
        result = {}
        for part in sorted(self.orders_dir.glob("order_date=*")):
            result.update(self.load_partition(part.name.split("=", 1)[1]))
        return result

    def reset(self) -> None:
        """Delete all warehouse data (used by --full-refresh)."""
        shutil.rmtree(self.root, ignore_errors=True)
