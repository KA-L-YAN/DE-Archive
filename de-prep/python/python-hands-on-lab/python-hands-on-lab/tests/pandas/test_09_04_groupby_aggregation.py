"""Tests for 09_pandas/04_groupby_aggregation.ipynb

Run: pytest tests/pandas/test_09_04_groupby_aggregation.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/04_groupby_aggregation.ipynb")


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

def test_revenue_by():
    assert nb.revenue_by(make_orders(), "country").to_dict() == {"FI": 19500.0, "IN": 2074.5}
    assert list(nb.revenue_by(make_orders(), "channel").index) == ["app", "web", "store"]


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

def test_summary_by():
    out = nb.summary_by(make_orders(), ["country"])
    assert out.to_dict("records") == [
        {"country": "FI", "orders": 2, "units": 4, "revenue": 19500.0, "avg_order_value": 9750.0, "customers": 1},
        {"country": "IN", "orders": 4, "units": 9, "revenue": 2124.5, "avg_order_value": 531.12, "customers": 2}]
    assert len(nb.summary_by(make_orders(), ["country", "channel"])) == 4


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

def test_daily_channel_pivot():
    p = nb.daily_channel_pivot(make_orders())
    assert list(p.index) == ["2026-01-01", "2026-01-02", "2026-01-03"] and list(p.columns) == ["app", "store", "web", "total"]
    assert p.loc["2026-01-01"].tolist() == [12000.0, 0.0, 1000.0, 13000.0] and p.loc["2026-01-02", "web"] == 0


def test_rfm():
    df = pd.DataFrame({"customer_id": ["A", "A", "B", "C", "C", "C", "D"], "order_id": ["1", "2", "3", "4", "5", "6", "7"],
                       "status": ["SHIPPED"] * 6 + ["CANCELLED"], "amount": [10.0, 20.0, 500.0, 1.0, 1.0, 1.0, 999.0],
                       "order_date": pd.to_datetime(["2026-01-01", "2026-01-09", "2026-01-05", "2025-12-01", "2025-12-02", "2025-12-03", "2026-01-10"])})
    out = nb.rfm(df, "2026-01-10")
    assert list(out.index) == ["A", "B", "C"]
    assert out["recency_days"].tolist() == [1, 5, 38] and out["frequency"].tolist() == [2, 1, 3] and out["rfm_score"].tolist() == ["322", "213", "131"]


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

def test_daily_metrics():
    out = nb.daily_metrics(make_orders())
    assert len(out) == 6 and out["country"].tolist() == ["FI"] * 3 + ["IN"] * 3
    fi = out[out.country == "FI"]
    assert fi["revenue"].tolist() == [12000.0, 0.0, 7500.0] and fi["rolling_7d"].round(2).tolist() == [12000.0, 6000.0, 6500.0]
    assert pd.isna(fi["dod_change"].iloc[0]) and fi["dod_change"].tolist()[1:] == [-12000.0, 7500.0]
    in_ = out[out.country == "IN"]
    assert in_["share_of_day"].tolist() == [0.0769, 1.0, 0.01]
    assert pd.api.types.is_datetime64_any_dtype(out["order_date"])
