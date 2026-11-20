"""Paginated extraction from the three API endpoints.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
from typing import Iterator
from .client import ApiClient

def iter_customers(client: ApiClient, page_size: int=100, max_pages: int=10000) -> Iterator[dict]:
    """Page-number pagination over /customers until page >= total_pages (or an empty page)."""
    raise NotImplementedError('TODO: implement iter_customers')

def iter_orders(client: ApiClient, limit: int=100, max_pages: int=10000) -> Iterator[dict]:
    """Cursor pagination over /orders following next_cursor until it is null."""
    raise NotImplementedError('TODO: implement iter_orders')

def fetch_events(client: ApiClient, since: str, limit: int=100, max_pages: int=10000) -> tuple[list[dict], str]:
    """Incremental pull from /events?since=W. Returns (events deduped by event_id, new_watermark).

    The watermark advances to each response's max_updated_at and never goes backwards; with no new
    events the original `since` is returned.
    """
    raise NotImplementedError('TODO: implement fetch_events')
