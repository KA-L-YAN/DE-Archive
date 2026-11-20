"""Tests for 09_pandas/03_transformations_vectorized.ipynb

Run: pytest tests/pandas/test_09_03_transformations_vectorized.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/03_transformations_vectorized.ipynb")


def test_add_amounts():
    df = pd.DataFrame({"quantity": [2, 1], "unit_price": [10.0, 99.99]})
    out = nb.add_amounts(df)
    assert out[["amount", "tax", "total"]].to_dict("list") == {"amount": [20.0, 99.99], "tax": [3.6, 18.0], "total": [23.6, 117.99]}
    assert list(df.columns) == ["quantity", "unit_price"]


def test_clean_text_columns():
    df = pd.DataFrame({"channel": [" WEB ", "App", ""], "status": ["shipped ", " placed", None], "country": ["in", " fi", "IN"], "name": ["  pavan   KALYAN ", "diya", ""]})
    out = nb.clean_text_columns(df)
    assert out["channel"].tolist()[:2] == ["web", "app"] and pd.isna(out["channel"].iloc[2])
    assert out["status"].tolist()[:2] == ["SHIPPED", "PLACED"] and pd.isna(out["status"].iloc[2])
    assert out["country"].tolist() == ["IN", "FI", "IN"] and out["name"].tolist()[:2] == ["Pavan Kalyan", "Diya"] and pd.isna(out["name"].iloc[2])
    assert df["channel"].iloc[0] == " WEB "


def test_add_buckets():
    df = pd.DataFrame({"amount": [0, 999.99, 1000, 9999, 10000, -5, None]})
    out = nb.add_buckets(df)
    assert out["amount_bucket"].astype(object).where(out["amount_bucket"].notna(), None).tolist() == ["<1k", "<1k", "1k-10k", "1k-10k", "10k+", None, None]
    assert out["is_large"].tolist() == [False, False, False, False, True, False, False]


def test_risk_level():
    base = {"amount": 500.0, "currency": "INR", "hour": 14, "country": "IN", "home_country": "in", "failed_attempts": 0}
    overrides = [{}, {"amount": 200001.0}, {"failed_attempts": 3}, {"failed_attempts": None}, {"country": "US", "amount": 50001.0}, {"country": "US", "amount": 50000.0},
                 {"hour": 4, "amount": 10001.0}, {"hour": 5, "amount": 10001.0}, {"currency": "usd"}, {"currency": "inr"}]
    df = pd.DataFrame([{**base, **o} for o in overrides])
    r = nb.risk_level(df)
    assert r.name == "risk" and r.tolist() == ["LOW", "HIGH", "HIGH", "LOW", "HIGH", "MEDIUM", "MEDIUM", "LOW", "MEDIUM", "LOW"]


def test_sessionize():
    ts = pd.to_datetime(["2026-01-01 10:00", "2026-01-01 10:20", "2026-01-01 11:00", "2026-01-01 09:00", "2026-01-01 10:50", "2026-01-01 10:30"])
    ev = pd.DataFrame({"user_id": ["u1", "u1", "u1", "u2", "u1", "u1"], "ts": ts})
    out = nb.sessionize(ev, gap_minutes=30)
    got = dict(zip(out["ts"].dt.strftime("%H:%M") + "-" + out["user_id"], out["session_id"]))
    assert got == {"10:00-u1": "u1-1", "10:20-u1": "u1-1", "10:30-u1": "u1-1", "10:50-u1": "u1-1", "11:00-u1": "u1-1", "09:00-u2": "u2-1"}
    out2 = nb.sessionize(ev, gap_minutes=15)
    assert sorted(out2.loc[out2.user_id == "u1", "session_id"].unique()) == ["u1-1", "u1-2", "u1-3"]
    s = out2.attrs["sessions"]
    assert s["session_id"].tolist() == ["u1-1", "u1-2", "u1-3", "u2-1"] and s["events"].tolist() == [1, 2, 2, 1]
    assert s["duration_min"].tolist() == [0.0, 10.0, 10.0, 0.0]
    assert "session_no" not in out.columns and len(out) == len(ev)
