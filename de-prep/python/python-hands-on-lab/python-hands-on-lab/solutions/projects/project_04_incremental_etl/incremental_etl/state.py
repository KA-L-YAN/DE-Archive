"""Durable pipeline state: processed files (by content hash), a global order index, run history."""
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
        self.path = Path(path)
        self.files: dict[str, dict] = {}
        self.order_index: dict[str, str] = {}
        self.runs: list[dict] = []
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise StateError(f"corrupt state file {self.path}") from exc
            if data.get("version") != self.VERSION:
                raise StateError(f"unsupported state version {data.get('version')!r}")
            self.files, self.order_index, self.runs = data["files"], data["order_index"], data["runs"]

    def is_processed(self, key: str, sha256: str) -> bool:
        """True if this exact file (same key and content) was already handled."""
        entry = self.files.get(key)
        return entry is not None and entry["sha256"] == sha256

    def processed_hashes(self) -> dict[str, str]:
        """sha256 -> key for every file whose content was processed (used to detect re-deliveries)."""
        return {e["sha256"]: k for k, e in self.files.items() if e["status"] == "processed"}

    def record_file(self, key: str, sha256: str, rows: int, run_id: str, status: str = "processed") -> None:
        """Remember a handled file."""
        self.files[key] = {"sha256": sha256, "rows": rows, "run_id": run_id, "status": status}

    def record_run(self, summary: dict) -> None:
        """Append a run summary (keep the last 50)."""
        self.runs = (self.runs + [summary])[-50:]

    def save(self) -> None:
        """Atomically persist the state (temp file + os.replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": self.VERSION, "files": self.files, "order_index": self.order_index, "runs": self.runs,
                   "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
