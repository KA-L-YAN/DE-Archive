"""Validation, cleaning, transformation, dedup and aggregation — pure functions, no I/O.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

class ValidationError(ValueError):
    """A row failed validation. `field` names the first offending column."""

    def __init__(self, field: str, message: str):
        """[provided]"""
        super().__init__(f'{field}: {message}')
        self.field = field

def parse_ts(value: str, field: str) -> datetime:
    """ISO-8601 (with optional Z) -> aware UTC datetime, else ValidationError."""
    raise NotImplementedError('TODO: implement parse_ts')

def validate_row(raw: dict, required: Iterable[str], allowed_status: Iterable[str]) -> dict:
    """Clean + type one raw row or raise ValidationError (first problem wins).

    Output: order_id, customer_id, product_id (stripped), quantity:int>=1, unit_price:float>=0,
    order_ts/updated_at: aware datetimes (updated_at must not be before order_ts),
    status (upper, allowed), channel (lower), country (upper, 2 letters), plus `_source`/`_line`.
    """
    raise NotImplementedError('TODO: implement validate_row')

def transform(record: dict, customers: dict[str, dict]) -> dict:
    """Add amount (2 dp), order_date (UTC date ISO), customer_segment (or 'unknown'), is_known_customer."""
    raise NotImplementedError('TODO: implement transform')

def dedupe_latest(records: Iterable[dict], key: str, version: str) -> tuple[list[dict], int]:
    """Keep the record with the greatest `version` per `key` (ties: later wins). Returns (records sorted by key, removed)."""
    raise NotImplementedError('TODO: implement dedupe_latest')

def daily_summary(records: Iterable[dict]) -> list[dict]:
    """Per (order_date, country, channel) excluding CANCELLED: orders, units, revenue (2 dp). Sorted by the key."""
    raise NotImplementedError('TODO: implement daily_summary')

def customer_summary(records: Iterable[dict]) -> list[dict]:
    """Per customer excluding CANCELLED: orders, revenue (2 dp), first_order, last_order (dates), segment. Sorted by revenue desc, id."""
    raise NotImplementedError('TODO: implement customer_summary')
