"""Tests for 07_apis/03_pagination.ipynb

Run: pytest tests/apis/test_07_03_pagination.py -v
"""
import pytest

from labkit.testing import load
from labkit.mock_api import MockSession, BASE_URL
import requests

nb = load("07_apis/03_pagination.ipynb")


def test_fetch_all_customers():
    s = MockSession(data={"customers": [{"customer_id": i} for i in range(237)]})
    out = nb.fetch_all_customers(s, BASE_URL, page_size=50)
    assert [c["customer_id"] for c in out] == list(range(237)) and len(s.calls) == 5
    assert nb.fetch_all_customers(MockSession(data={"customers": []}), BASE_URL) == []


def test_iter_orders_lazy():
    from itertools import islice
    s = MockSession(data={"orders": [{"order_id": i} for i in range(250)]})
    gen = nb.iter_orders(s, BASE_URL, limit=100)
    assert s.calls == []
    assert [o["order_id"] for o in islice(gen, 5)] == [0, 1, 2, 3, 4] and len(s.calls) == 1
    assert len(list(gen)) == 245 and len(s.calls) == 3
    assert "cursor" not in s.calls[0][2] and s.calls[1][2]["cursor"] == "c_100"


def test_iter_products():
    s = MockSession(data={"products": [{"product_id": i} for i in range(120)]})
    assert [p["product_id"] for p in nb.iter_products(s, f"{BASE_URL}/products", limit=50)] == list(range(120)) and len(s.calls) == 3

def test_iter_products_loop_detection():
    class LoopSession:
        def get(self, url, params=None, timeout=None):
            class R:
                status_code = 200
                def raise_for_status(self): pass
                def json(self): return {"results": [1], "next": "https://x/products?offset=50"}
            return R()
    iter_products = nb.iter_products    # bind first (NotImplementedError is a RuntimeError subclass)
    with pytest.raises(RuntimeError, match="loop"):
        list(iter_products(LoopSession(), "https://x/products"))


def test_pull_events():
    evs = [{"event_id": f"e{i}", "updated_at": f"2026-01-01T00:00:{i:02d}Z"} for i in range(45)]
    s = MockSession(data={"events": evs})
    got, wm = nb.pull_events(s, BASE_URL, since="2026-01-01T00:00:09Z", limit=10)
    assert [e["event_id"] for e in got] == [f"e{i}" for i in range(10, 45)] and wm == "2026-01-01T00:00:44Z"
    again, wm2 = nb.pull_events(s, BASE_URL, since=wm, limit=10)
    assert again == [] and wm2 == wm

def test_pull_events_real_feed():
    s = MockSession()
    got, wm = nb.pull_events(s, BASE_URL, since="", limit=100)
    unique = {e["event_id"] for e in s.data["events"]}
    # Known limitation of a pure timestamp watermark: events sharing an updated_at across a page boundary get skipped.
    assert len(unique) - 5 <= len(got) <= len(unique) and wm == max(e["updated_at"] for e in s.data["events"])


def test_paginate_all_styles():
    s = MockSession(data={"customers": [{"i": i} for i in range(130)], "orders": [{"i": i} for i in range(130)], "products": [{"i": i} for i in range(130)]})
    assert len(list(nb.paginate(s, f"{BASE_URL}/customers", "page", "data", page_size=50))) == 130
    assert len(list(nb.paginate(s, f"{BASE_URL}/orders", "cursor", "items", page_size=50))) == 130
    assert len(list(nb.paginate(s, f"{BASE_URL}/products", "link", "results", page_size=50))) == 130

def test_paginate_max_pages_and_validation():
    s = MockSession(data={"orders": [{"i": i} for i in range(1000)]})
    assert len(list(nb.paginate(s, f"{BASE_URL}/orders", "cursor", "items", page_size=100, max_pages=3))) == 300 and len(s.calls) == 3
    with pytest.raises(ValueError):
        nb.paginate(s, f"{BASE_URL}/orders", "offset", "items")
