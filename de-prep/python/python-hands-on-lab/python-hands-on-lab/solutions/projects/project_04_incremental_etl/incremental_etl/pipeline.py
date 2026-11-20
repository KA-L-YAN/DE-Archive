"""Incremental, idempotent, crash-safe orchestration with per-file checkpoints."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .processing import classify, discover, parse_file, select_changes
from .state import PipelineState
from .warehouse import Warehouse

log = logging.getLogger("incremental_etl")


class SimulatedCrash(RuntimeError):
    """Raised by `run(..., crash_after_files=n)` to test recovery."""


def run(input_dir: str | Path, warehouse_dir: str | Path, state_path: str | Path, *, run_id: str | None = None,
        full_refresh: bool = False, crash_after_files: int | None = None) -> dict:
    """Process everything new or changed since the last run.

    For each new/changed file, in partition order:
      parse + validate → reject to quarantine → keep only versions newer than the global order index →
      upsert affected warehouse partitions → update order index + file record → save state   (checkpoint)
    Unchanged files are skipped; re-delivered files (same content, new name) are recorded and skipped.
    `crash_after_files=n` raises SimulatedCrash after n files have been checkpointed.
    Returns a run summary (also appended to the state's run history).
    """
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    warehouse = Warehouse(warehouse_dir)
    if full_refresh:
        warehouse.reset()
        Path(state_path).unlink(missing_ok=True)
    state = PipelineState(state_path)
    started = time.perf_counter()
    files = discover(input_dir)
    groups = classify(files, state.files, state.processed_hashes())
    summary = {"run_id": run_id, "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "files_seen": len(files), "files_processed": 0, "files_unchanged": len(groups["unchanged"]),
               "files_redelivered": len(groups["redelivered"]), "files_changed": len(groups["changed"]),
               "rows_read": 0, "rows_rejected": 0, "rows_upserted": 0, "rows_stale": 0, "partitions_touched": []}
    touched: set[str] = set()

    for f in groups["redelivered"]:
        state.record_file(f.key, f.sha256, rows=0, run_id=run_id, status="redelivered")
        log.warning("skipping re-delivered file %s (same content as an already processed file)", f.key)
    if groups["redelivered"]:
        state.save()

    to_process = sorted(groups["new"] + groups["changed"], key=lambda f: (f.partition, f.key))
    for n, f in enumerate(to_process, start=1):
        valid, rejects = parse_file(f)
        upserts, stale = select_changes(valid, state.order_index)
        warehouse.quarantine(rejects, run_id, f.key)
        touched.update(warehouse.upsert(upserts))
        for r in upserts:
            state.order_index[r["order_id"]] = r["updated_at"]
        state.record_file(f.key, f.sha256, rows=len(valid) + len(rejects), run_id=run_id)
        state.save()                                      # checkpoint after every file
        summary["files_processed"] += 1
        summary["rows_read"] += len(valid) + len(rejects)
        summary["rows_rejected"] += len(rejects)
        summary["rows_upserted"] += len(upserts)
        summary["rows_stale"] += stale
        log.info(json.dumps({"event": "file_processed", "run_id": run_id, "file": f.key, "valid": len(valid),
                             "rejected": len(rejects), "upserted": len(upserts), "stale": stale}))
        if crash_after_files is not None and n >= crash_after_files:
            raise SimulatedCrash(f"simulated crash after {n} files")

    summary["partitions_touched"] = sorted(touched)
    summary["duration_seconds"] = round(time.perf_counter() - started, 3)
    summary["orders_in_warehouse"] = len(state.order_index)
    state.record_run(summary)
    state.save()
    return summary


def status(state_path: str | Path) -> dict:
    """Small status report from the state file (no input scanning)."""
    state = PipelineState(state_path)
    by_status: dict[str, int] = {}
    for entry in state.files.values():
        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1
    last = state.runs[-1] if state.runs else None
    return {"files": by_status, "orders": len(state.order_index), "runs": len(state.runs),
            "last_run": {k: last[k] for k in ("run_id", "started_at", "files_processed", "rows_upserted")} if last else None}
