"""Tests for 09_pandas/01_dataframe_basics_io.ipynb

Run: pytest tests/pandas/test_09_01_dataframe_basics_io.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/01_dataframe_basics_io.ipynb")


def test_load_orders():
    from pathlib import Path
    df = nb.load_orders(Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv")
    assert len(df) > 5000 and pd.api.types.is_numeric_dtype(df["quantity"]) and pd.api.types.is_numeric_dtype(df["unit_price"])
    assert str(df["order_ts"].dt.tz) == "UTC" and df["order_ts"].isna().sum() > 10 and df["unit_price"].isna().sum() > 10
    assert df["customer_id"].dropna().map(type).eq(str).all()


def test_series_stats():
    r = nb.series_stats(pd.Series([1, 2, 3, 4, None, 100]))
    assert r == {"count": 5, "nulls": 1, "mean": 22.0, "median": 3.0, "p95": 80.8, "min": 1.0, "max": 100.0}
    assert type(r["count"]) is int and type(r["mean"]) is float
    assert nb.series_stats(pd.Series([None, None], dtype=float))["mean"] is None


def test_load_order_items():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "datasets/json/orders_nested.json"
    df = nb.load_order_items(p)
    data = json.loads(p.read_text())
    assert len(df) == sum(len(o["items"]) for o in data)
    assert list(df.columns) == ["order_id", "created_at", "status", "customer_id", "country", "payment_status", "product_id", "name", "category", "qty", "price", "line_total"]
    assert df["payment_status"].isna().sum() > 0 and (df["line_total"] == df["qty"] * df["price"]).all()


def test_profile():
    df = pd.DataFrame({"a": [1, None, 3, 3], "b": ["x", " ", None, "x"], "c": [None, None, None, None]})
    p = nb.profile(df)
    assert list(p.index) == ["a", "b", "c"]
    assert p.loc["a", "nulls"] == 1 and p.loc["a", "distinct"] == 2 and p.loc["a", "null_pct"] == 25.0 and p.loc["a", "example"] == "1.0"
    assert p.loc["b", "empty_strings"] == 1 and p.loc["b", "distinct"] == 2 and pd.isna(p.loc["c", "example"]) and p.loc["c", "non_null"] == 0


def test_revenue_by_country_chunked(tmp_path):
    p = tmp_path / "o.csv"
    p.write_text("order_id,quantity,unit_price,country\nO1,2,10,IN\nO2,1,5,FI\nO3,x,5,FI\nO4,1,1.5,IN\nO4,1,1.5,IN\nO5,0,9,IN\n")
    s = nb.revenue_by_country_chunked(p, chunksize=2)
    assert s.name == "revenue" and s.index.name == "country" and s.to_dict() == {"IN": 23.0, "FI": 5.0}
    assert list(s.index) == ["IN", "FI"]

def test_chunked_matches_full():
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv"
    big = nb.revenue_by_country_chunked(p, chunksize=100_000)
    small = nb.revenue_by_country_chunked(p, chunksize=700)
    # orders.csv is shuffled, so duplicates land in different small chunks and survive per-chunk dedup:
    assert set(big.index) == set(small.index) and (small.reindex(big.index) >= big).all() and (small.reindex(big.index) > big).any()
