"""Durable pipeline state: processed files (by content hash), a global order index, run history.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

class StateError(RuntimeError):
    """The state file exists but cannot be trusted (corrupt / wrong version)."""

class PipelineState:
    """JSON-backed state. Shape on disk:

    {"version": 1,
     "files": {"dt=2026-01-01/orders_x.csv": {"sha256": "...", "rows": 120, "run_id": "...", "status": "processed"|"redelivered"}},
     "order_index": {"O0300001": "2026-01-01T12:00:00Z"},      # latest updated_at loaded per order
     "runs": [{"run_id": ..., "started_at": ..., "files_processed": n, ...}]}
    """
    VERSION = 1

    def __init__(self, path: str | Path):
        """Load existing state from `path` (or start empty). Corrupt JSON or a wrong version -> StateError."""
        raise NotImplementedError('TODO: implement __init__')

    def is_processed(self, key: str, sha256: str) -> bool:
        """True if this exact file (same key and content) was already handled."""
        raise NotImplementedError('TODO: implement is_processed')

    def processed_hashes(self) -> dict[str, str]:
        """sha256 -> key for every file whose content was processed (used to detect re-deliveries)."""
        raise NotImplementedError('TODO: implement processed_hashes')

    def record_file(self, key: str, sha256: str, rows: int, run_id: str, status: str='processed') -> None:
        """Remember a handled file."""
        raise NotImplementedError('TODO: implement record_file')

    def record_run(self, summary: dict) -> None:
        """Append a run summary (keep the last 50)."""
        raise NotImplementedError('TODO: implement record_run')

    def save(self) -> None:
        """Atomically persist the state (temp file + os.replace)."""
        raise NotImplementedError('TODO: implement save')
