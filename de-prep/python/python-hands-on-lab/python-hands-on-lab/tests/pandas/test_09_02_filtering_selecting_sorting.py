"""Tests for 09_pandas/02_filtering_selecting_sorting.ipynb

Run: pytest tests/pandas/test_09_02_filtering_selecting_sorting.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/02_filtering_selecting_sorting.ipynb")


def make_orders():
    return pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4", "O5", "O6"],
        "customer_id": ["C1", "C2", "C1", "C3", "C2", "C1"],
        "channel": ["web", "app", "web", "store", "web", "web"],
        "country": ["IN", "FI", "IN", "IN", "FI", "IN"],
        "status": ["SHIPPED", "PLACED", "CANCELLED", "DELIVERED", "SHIPPED", "PLACED"],
        "quantity": [2, 1, 5, 1, 3, 1],
        "unit_price": [500.0, 12000.0, 10.0, 999.0, 2500.0, 75.5],
        "order_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03", "2026-01-03"]),
    }).assign(amount=lambda d: d.quantity * d.unit_price)

def test_big_web_orders():
    out = nb.big_web_orders(make_orders(), 75)
    assert out.to_dict("records") == [{"order_id": "O5", "customer_id": "C2", "amount": 7500.0}, {"order_id": "O1", "customer_id": "C1", "amount": 1000.0},
                                      {"order_id": "O6", "customer_id": "C1", "amount": 75.5}]
    assert list(out.index) == [0, 1, 2] and nb.big_web_orders(make_orders(), 1e9).empty


def make_orders():
    return pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4", "O5", "O6"],
        "customer_id": ["C1", "C2", "C1", "C3", "C2", "C1"],
        "channel": ["web", "app", "web", "store", "web", "web"],
        "country": ["IN", "FI", "IN", "IN", "FI", "IN"],
        "status": ["SHIPPED", "PLACED", "CANCELLED", "DELIVERED", "SHIPPED", "PLACED"],
        "quantity": [2, 1, 5, 1, 3, 1],
        "unit_price": [500.0, 12000.0, 10.0, 999.0, 2500.0, 75.5],
        "order_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03", "2026-01-03"]),
    }).assign(amount=lambda d: d.quantity * d.unit_price)

def test_query_orders():
    df = make_orders()
    assert list(nb.query_orders(df, ["SHIPPED", "PLACED"], None, "2026-01-01", "2026-01-02").order_id) == ["O1", "O2"]
    assert list(nb.query_orders(df, ["SHIPPED", "PLACED"], ["IN"], "2026-01-01", "2026-01-03").index) == [0, 5]


def make_orders():
    return pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4", "O5", "O6"],
        "customer_id": ["C1", "C2", "C1", "C3", "C2", "C1"],
        "channel": ["web", "app", "web", "store", "web", "web"],
        "country": ["IN", "FI", "IN", "IN", "FI", "IN"],
        "status": ["SHIPPED", "PLACED", "CANCELLED", "DELIVERED", "SHIPPED", "PLACED"],
        "quantity": [2, 1, 5, 1, 3, 1],
        "unit_price": [500.0, 12000.0, 10.0, 999.0, 2500.0, 75.5],
        "order_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03", "2026-01-03"]),
    }).assign(amount=lambda d: d.quantity * d.unit_price)

def test_top_n_per_group():
    out = nb.top_n_per_group(make_orders(), "country", "amount", n=2)
    assert list(zip(out.country, out.order_id)) == [("FI", "O2"), ("FI", "O5"), ("IN", "O1"), ("IN", "O4")]
    assert len(nb.top_n_per_group(make_orders(), "country", "amount", n=10)) == 6


def test_latest_versions():
    df = pd.DataFrame({"order_id": ["B", "A", "B", "A", "C", "C"], "updated_at": pd.to_datetime(["2026-01-02", "2026-01-05", None, "2026-01-05", None, None]),
                       "status": ["b1", "a1", "b_nat", "a2", "c1", "c2"]})
    out = nb.latest_versions(df)
    assert out.to_dict("list")["status"] == ["a2", "b1", "c2"] and out.attrs["dropped"] == 3 and list(out.index) == [0, 1, 2]


def test_apply_rules():
    df = pd.DataFrame({"quantity": [1, 0, 2, None], "status": ["PLACED", "PLACED", "LOST", "SHIPPED"], "unit_price": [1.0, 2.0, -1.0, 3.0]}, index=[10, 11, 12, 13])
    rules = {"positive_qty": "quantity > 0", "known_status": "status in ['PLACED', 'SHIPPED']", "price_ok": "unit_price >= 0"}
    good, bad = nb.apply_rules(df, rules)
    assert list(good.index) == [10] and list(bad.index) == [11, 12, 13]
    assert bad["failed_rules"].tolist() == ["positive_qty", "known_status,price_ok", "positive_qty"]
