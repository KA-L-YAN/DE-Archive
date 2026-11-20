"""Paginated extraction from the three API endpoints."""
from __future__ import annotations

from typing import Iterator

from .client import ApiClient


def iter_customers(client: ApiClient, page_size: int = 100, max_pages: int = 10_000) -> Iterator[dict]:
    """Page-number pagination over /customers until page >= total_pages (or an empty page)."""
    page = 1
    while page <= max_pages:
        body = client.get_json("customers", {"page": page, "page_size": page_size})
        data = body.get("data") or []
        yield from data
        if not data or page >= body.get("total_pages", page):
            return
        page += 1


def iter_orders(client: ApiClient, limit: int = 100, max_pages: int = 10_000) -> Iterator[dict]:
    """Cursor pagination over /orders following next_cursor until it is null."""
    cursor = None
    for _ in range(max_pages):
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        body = client.get_json("orders", params)
        yield from body.get("items") or []
        cursor = body.get("next_cursor")
        if not cursor:
            return


def fetch_events(client: ApiClient, since: str, limit: int = 100, max_pages: int = 10_000) -> tuple[list[dict], str]:
    """Incremental pull from /events?since=W. Returns (events deduped by event_id, new_watermark).

    The watermark advances to each response's max_updated_at and never goes backwards; with no new
    events the original `since` is returned.
    """
    watermark, events, seen = since, [], set()
    for _ in range(max_pages):
        body = client.get_json("events", {"since": watermark, "limit": limit})
        batch = body.get("events") or []
        if not batch:
            break
        for e in batch:
            if e["event_id"] not in seen:
                seen.add(e["event_id"])
                events.append(e)
        watermark = max(watermark, body["max_updated_at"])
    return events, watermark
