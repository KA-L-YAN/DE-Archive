"""Tests for 08_data_engineering_python/03_transformations.ipynb

Run: pytest tests/etl/test_08_03_transformations.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/03_transformations.ipynb")


def test_normalize_customer():
    raw = {"customer_id": "C1", "name": "  PAVAN   KALYAN ", "email": " P.K@Example.COM ", "country": "in", "signup_date": "15/03/2025", "is_active": "TRUE"}
    out = nb.normalize_customer(raw)
    assert out == {"customer_id": "C1", "name": "Pavan Kalyan", "email": "p.k@example.com", "country": "IN", "signup_date": "2025-03-15", "is_active": True}
    assert raw["country"] == "in"
    assert nb.normalize_customer({"email": "", "signup_date": "2025-31-01"})["email"] is None
    assert nb.normalize_customer({"signup_date": "2025-31-01"})["signup_date"] is None


def test_enrich_orders():
    customers = [{"customer_id": "C1", "segment": "smb", "country": "IN"}]
    products = [{"product_id": "P1", "category": "Books", "name": "Spark Guide"}, {"product_id": "P2", "category": "", "name": "X"}]
    out = nb.enrich_orders([{"order_id": 1, "customer_id": "C1", "product_id": "P1"}, {"order_id": 2, "customer_id": "C9", "product_id": "P2"}], customers, products)
    assert out[0] == {"order_id": 1, "customer_id": "C1", "product_id": "P1", "customer_segment": "smb", "customer_country": "IN", "product_category": "Books", "product_name": "Spark Guide"}
    assert out[1]["customer_segment"] is None and out[1]["product_category"] is None and out[1]["product_name"] == "X"


def test_derive():
    from datetime import datetime, timezone
    o = {"order_id": 1, "order_ts": datetime(2026, 1, 9, 19, 0, tzinfo=timezone.utc), "amount": 1000}
    d = nb.derive(o)
    assert (d["order_date"], d["order_hour_ist"], d["weekday"], d["is_weekend"], d["amount_bucket"]) == ("2026-01-09", 0, "Saturday", True, "1k-10k")
    assert nb.derive({**o, "amount": 999.99})["amount_bucket"] == "<1k" and nb.derive({**o, "amount": 10_000})["amount_bucket"] == "10k+"
    assert "weekday" not in o


def test_add_window_columns():
    rows = [{"acct": "B", "ts": 2, "amt": 5.0}, {"acct": "A", "ts": 3, "amt": 1.5}, {"acct": "A", "ts": 1, "amt": 10.0}, {"acct": "A", "ts": 3, "amt": 2.0}]
    out = nb.add_window_columns(rows, "acct", "ts", "amt")
    assert [(r["acct"], r["ts"], r["row_number"], r["running_total"], r["prev_value"]) for r in out] == [
        ("A", 1, 1, 10.0, None), ("A", 3, 2, 11.5, 10.0), ("A", 3, 3, 13.5, 1.5), ("B", 2, 1, 5.0, None)]
    assert nb.add_window_columns([], "a", "b", "c") == []


DIM = [{"customer_id": "C1", "city": "Hyderabad", "email": "k@x.io", "valid_from": "2025-01-01", "valid_to": None, "is_current": True},
       {"customer_id": "C2", "city": "Pune", "email": "d@x.io", "valid_from": "2025-01-01", "valid_to": None, "is_current": True}]

def test_apply_scd2():
    import copy
    before = copy.deepcopy(DIM)
    updates = [{"customer_id": "C1", "city": "Vijayawada", "email": "k@x.io"}, {"customer_id": "C2", "city": "Pune", "email": "new@x.io"},
               {"customer_id": "C3", "city": "Espoo", "email": "e@x.io"}]
    out = nb.apply_scd2(DIM, updates, "customer_id", ["city"], "2026-01-10")
    assert DIM == before
    assert [(r["customer_id"], r["city"], r["valid_from"], r["valid_to"], r["is_current"]) for r in out] == [
        ("C1", "Hyderabad", "2025-01-01", "2026-01-10", False), ("C1", "Vijayawada", "2026-01-10", None, True),
        ("C2", "Pune", "2025-01-01", None, True), ("C3", "Espoo", "2026-01-10", None, True)]
    assert out[2]["email"] == "new@x.io"
    again = nb.apply_scd2(out, updates, "customer_id", ["city"], "2026-01-11")
    assert again == out

def test_apply_scd2_duplicates():
    with pytest.raises(ValueError):
        nb.apply_scd2(DIM, [{"customer_id": "C1", "city": "a"}, {"customer_id": "C1", "city": "b"}], "customer_id", ["city"], "2026-01-01")
