"""Orchestration: discover → read → validate → transform → dedupe → aggregate → write → audit.

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
from . import io, rules
from .config import Config
log = logging.getLogger('csv_etl')
CLEAN_FIELDS = ['order_id', 'customer_id', 'product_id', 'quantity', 'unit_price', 'amount', 'order_ts', 'order_date', 'status', 'updated_at', 'channel', 'country', 'customer_segment', 'is_known_customer', '_source', '_line']
REJECT_FIELDS = ['_source', '_line', '_error_field', '_error', 'raw']

class RejectThresholdExceeded(RuntimeError):
    """Too many rows were rejected; the audit report is attached as `.audit`."""

    def __init__(self, audit: dict):
        """[provided]"""
        super().__init__(f"reject ratio {audit['totals']['reject_ratio']:.2%} exceeds limit")
        self.audit = audit

def _iso(dt: datetime) -> str:
    """Aware datetime -> 'YYYY-MM-DDTHH:MM:SSZ'."""
    raise NotImplementedError('TODO: implement _iso')

def run(config: Config, run_id: str | None=None, clock=time.perf_counter) -> dict:
    """Run the pipeline and return the audit dict (also written to output_dir/audit.json).

    Outputs (all written atomically):
      clean_orders.csv, daily_summary.csv, customer_summary.csv — only when the reject ratio is within limits
      rejected_rows.csv, audit.json — always
    Raises RejectThresholdExceeded (after writing rejects + audit) when the ratio is too high.
    """
    raise NotImplementedError('TODO: implement run')
