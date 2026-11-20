"""Incremental, idempotent, crash-safe orchestration with per-file checkpoints.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
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
log = logging.getLogger('incremental_etl')

class SimulatedCrash(RuntimeError):
    """Raised by `run(..., crash_after_files=n)` to test recovery."""

def run(input_dir: str | Path, warehouse_dir: str | Path, state_path: str | Path, *, run_id: str | None=None, full_refresh: bool=False, crash_after_files: int | None=None) -> dict:
    """Process everything new or changed since the last run.

    For each new/changed file, in partition order:
      parse + validate → reject to quarantine → keep only versions newer than the global order index →
      upsert affected warehouse partitions → update order index + file record → save state   (checkpoint)
    Unchanged files are skipped; re-delivered files (same content, new name) are recorded and skipped.
    `crash_after_files=n` raises SimulatedCrash after n files have been checkpointed.
    Returns a run summary (also appended to the state's run history).
    """
    raise NotImplementedError('TODO: implement run')

def status(state_path: str | Path) -> dict:
    """Small status report from the state file (no input scanning)."""
    raise NotImplementedError('TODO: implement status')
