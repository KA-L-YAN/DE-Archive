"""Tests for 07_apis/02_json_api_processing.ipynb

Run: pytest tests/apis/test_07_02_json_api_processing.py -v
"""
import pytest

from labkit.testing import load
from labkit.mock_api import MockSession, BASE_URL
import requests

nb = load("07_apis/02_json_api_processing.ipynb")


def test_extract_items():
    assert nb.extract_items({"data": [1]}) == [1] and nb.extract_items({"result": {"items": [2]}}, "result.items") == [2]
    assert nb.extract_items({}) == [] and nb.extract_items({"data": None}) == [] and nb.extract_items({"result": 5}, "result.items") == []
    with pytest.raises(TypeError):
        nb.extract_items({"data": {"a": 1}})


@pytest.mark.parametrize("raw, snake", [("customerId", "customer_id"), ("HTTPStatusCode", "http_status_code"), ("orderID", "order_id"),
                                        ("already_snake", "already_snake"), ("v2Name", "v2_name"), ("x", "x"), ("ship-to", "ship_to")])
def test_to_snake(raw, snake):
    assert nb.to_snake(raw) == snake

def test_snake_keys():
    doc = {"orderId": 1, "lineItems": [{"productId": "P1", "unitPrice": 2}], "shipTo": {"postalCode": "500001"}, "tags": ["camelCase"]}
    assert nb.snake_keys(doc) == {"order_id": 1, "line_items": [{"product_id": "P1", "unit_price": 2}], "ship_to": {"postal_code": "500001"}, "tags": ["camelCase"]}


from datetime import datetime as _dt, timezone as _tz

@pytest.mark.parametrize("value", ["2026-01-05T10:00:00Z", "2026-01-05T15:30:00+05:30", "2026-01-05T10:00:00", 1767607200, 1767607200000, "1767607200", 1767607200.0])
def test_parse_ts(value):
    assert nb.parse_ts(value) == _dt(2026, 1, 5, 10, 0, tzinfo=_tz.utc)
    assert nb.parse_ts(value).tzinfo is not None

@pytest.mark.parametrize("bad", ["yesterday", "", None, True, "2026-13-01T00:00:00Z"])
def test_parse_ts_invalid(bad):
    with pytest.raises(ValueError):
        nb.parse_ts(bad)


def test_normalize_orders():
    raw = [{"order_id": "O2", "customer_id": "C1", "product_id": "P1", "quantity": "2", "unit_price": 10.5, "status": "placed", "order_ts": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
           {"order_id": "O1", "customer_id": "C1", "product_id": "P1", "quantity": 1, "unit_price": None, "status": "x", "order_ts": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
           {"order_id": "O2", "customer_id": "C1", "product_id": "P1", "quantity": 2, "unit_price": 10.5, "status": "shipped", "order_ts": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"},
           {"order_id": "O2", "customer_id": "C1", "product_id": "P1", "quantity": 2, "unit_price": 10.5, "status": "stale", "order_ts": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T12:00:00Z"}]
    out = nb.normalize_orders(raw)
    assert [o["order_id"] for o in out] == ["O1", "O2"] and out[1]["status"] == "SHIPPED" and out[1]["amount"] == 21.0
    assert out[0]["amount"] is None and out[0]["order_ts"].tzinfo is not None

def test_normalize_orders_real_api_data():
    s = MockSession()
    raw = s.data["orders"]
    out = nb.normalize_orders(raw)
    assert len(out) == len({r["order_id"] for r in raw}) == 523 and sum(o["amount"] is None for o in out) >= 1


def test_reconcile():
    src = [{"id": 1, "amt": 10.0, "name": "a "}, {"id": 2, "amt": 5.0, "name": "b"}, {"id": 3, "amt": None, "name": "c"}, {"id": 3, "amt": 1.0, "name": "c"}]
    tgt = [{"id": 1, "amt": 10.004, "name": "a"}, {"id": 2, "amt": 6.0, "name": "B"}, {"id": 4, "amt": 1, "name": "d"}]
    r = nb.reconcile(src, tgt, "id", ["amt", "name"], tolerance=0.01)
    assert (r["source_count"], r["target_count"], r["matched"]) == (4, 3, 1)
    assert r["missing_in_target"] == [3] and r["unexpected_in_target"] == [4] and r["duplicate_keys"] == {"source": [3], "target": []}
    assert r["mismatches"] == [{"key": 2, "field": "amt", "source": 5.0, "target": 6.0}, {"key": 2, "field": "name", "source": "b", "target": "B"}]

def test_reconcile_none_and_empty():
    r = nb.reconcile([{"k": "x", "v": None}], [{"k": "x", "v": 0}], "k", ["v"])
    assert r["matched"] == 0 and len(r["mismatches"]) == 1
    assert nb.reconcile([], [], "k", ["v"])["matched"] == 0
