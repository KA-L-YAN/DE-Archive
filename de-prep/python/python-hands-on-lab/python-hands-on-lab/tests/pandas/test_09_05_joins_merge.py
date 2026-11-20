"""Tests for 09_pandas/05_joins_merge.ipynb

Run: pytest tests/pandas/test_09_05_joins_merge.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/05_joins_merge.ipynb")


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

def test_with_customers():
    cust = pd.DataFrame({"customer_id": ["C1", "C2"], "segment": ["smb", "retail"], "country": ["IN", "FI"]})
    out = nb.with_customers(make_orders(), cust)
    assert len(out) == 6 and "country_customer" in out and out.loc[out.customer_id == "C3", "segment"].isna().all()
    with pytest.raises(pd.errors.MergeError):
        nb.with_customers(make_orders(), pd.concat([cust, cust]))


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

def test_orphans():
    o = make_orders()
    o.loc[1, "customer_id"] = ""
    cust = pd.DataFrame({"customer_id": ["C1", "C1"]})
    out = nb.orphans(o, cust)
    assert out["order_id"].tolist() == ["O4", "O5"] and list(out.columns) == list(o.columns)


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

def test_enrich():
    o = make_orders().assign(product_id=["P1", "P2", "P1", "P9", "P2", "P1"])
    cust = pd.DataFrame({"customer_id": ["C1", "C2", "C3"], "segment": ["smb", "retail", "enterprise"]})
    prods = pd.DataFrame({"product_id": ["P1", "P2"], "category": ["Books", ""], "name": ["Spark Guide", "Desk"], "price": [400.0, 12000.0]})
    out = nb.enrich(o, cust, prods)
    assert out["category"].tolist() == ["Books", "UNKNOWN", "Books", "UNKNOWN", "UNKNOWN", "Books"]
    assert out["price_diff_pct"].tolist()[:2] == [25.0, 0.0] and pd.isna(out["price_diff_pct"].iloc[3]) and out["product_name"].iloc[0] == "Spark Guide"


def test_convert_currency():
    txns = pd.DataFrame({"txn_id": ["t1", "t2", "t3", "t4", "t5"], "ts": pd.to_datetime(["2026-01-20", "2026-01-01", "2026-02-02", "2025-12-01", "2026-01-15"]),
                         "currency": ["USD", "USD", "USD", "EUR", "INR"], "amount": [10.0, 10.0, 10.0, 5.0, 99.0]}, index=[5, 6, 7, 8, 9])
    rates = pd.DataFrame({"currency": ["USD", "EUR", "USD"], "effective_ts": pd.to_datetime(["2026-02-01", "2026-01-01", "2026-01-01"]), "rate_to_inr": [83.6, 90.0, 83.1]})
    out = nb.convert_currency(txns, rates)
    assert list(out.index) == [5, 6, 7, 8, 9] and out["txn_id"].tolist() == ["t1", "t2", "t3", "t4", "t5"]
    assert out["amount_inr"].tolist()[:3] == [831.0, 831.0, 836.0] and pd.isna(out["amount_inr"].iloc[3]) and out["amount_inr"].iloc[4] == 99.0


def test_reconcile_frames():
    src = pd.DataFrame({"id": [1, 2, 3, 4], "amt": [10.0, 5.0, None, 1.0], "name": ["a", "b", "c", None]})
    tgt = pd.DataFrame({"id": [1, 2, 3, 5], "amt": [10.004, 6.0, None, 1.0], "name": ["a", "B", "c", "e"]})
    summary, mm = nb.reconcile_frames(src, tgt, "id", ["amt", "name"], tolerance=0.01)
    assert summary == {"source_rows": 4, "target_rows": 4, "only_in_source": 1, "only_in_target": 1, "in_both": 3, "rows_with_mismatch": 1}
    assert mm.to_dict("records") == [{"key": 2, "column": "amt", "source": 5.0, "target": 6.0}, {"key": 2, "column": "name", "source": "b", "target": "B"}]

def test_reconcile_frames_duplicates():
    with pytest.raises(pd.errors.MergeError):
        nb.reconcile_frames(pd.DataFrame({"id": [1, 1], "v": [1, 2]}), pd.DataFrame({"id": [1], "v": [1]}), "id", ["v"])
