"""A tiny file-based 'warehouse': a current-state orders table partitioned by order_date + a quarantine area.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
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
        raise NotImplementedError('TODO: implement __init__')

    def _partition_file(self, order_date: str) -> Path:
        """Path of the single part file for an order_date partition."""
        raise NotImplementedError('TODO: implement _partition_file')

    def load_partition(self, order_date: str) -> dict[str, dict]:
        """order_id -> row for one partition ({} if absent)."""
        raise NotImplementedError('TODO: implement load_partition')

    def _write_partition(self, order_date: str, rows: dict[str, dict]) -> None:
        """Atomically write rows (sorted by order_id) to the partition file."""
        raise NotImplementedError('TODO: implement _write_partition')

    def upsert(self, records: Iterable[dict]) -> dict[str, int]:
        """Merge records into their order_date partitions, rewriting each affected partition atomically.

        Returns {order_date: rows_written_into_it}. Records must already be the winning versions.
        """
        raise NotImplementedError('TODO: implement upsert')

    def quarantine(self, rejects: list[dict], run_id: str, source_key: str) -> Path | None:
        """Write rejected rows for one source file; returns the path (None when there are no rejects)."""
        raise NotImplementedError('TODO: implement quarantine')

    def all_orders(self) -> dict[str, dict]:
        """Every current order across partitions."""
        raise NotImplementedError('TODO: implement all_orders')

    def reset(self) -> None:
        """Delete all warehouse data (used by --full-refresh)."""
        raise NotImplementedError('TODO: implement reset')
