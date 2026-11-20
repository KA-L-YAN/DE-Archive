"""Tests for 09_pandas/06_data_cleaning.ipynb

Run: pytest tests/pandas/test_09_06_data_cleaning.py -v
"""
import pytest

from labkit.testing import load
import numpy as np
import pandas as pd

nb = load("09_pandas/06_data_cleaning.ipynb")


def test_standardize_columns():
    df = pd.DataFrame(columns=[" Order ID ", "customerName", "unit-price(INR)", "OrderID2"])
    assert list(nb.standardize_columns(df).columns) == ["order_id", "customer_name", "unit_price_inr", "order_id2"]
    with pytest.raises(ValueError):
        nb.standardize_columns(pd.DataFrame(columns=["A B", "a_b"]))


def test_fill_missing():
    df = pd.DataFrame({"q": [1.0, None, 3.0, 10.0], "s": ["a", "", None, " "], "d": pd.to_datetime(["2026-01-01", None, None, None]), "ok": [1, 2, 3, 4]})
    out, rep = nb.fill_missing(df)
    assert out["q"].tolist() == [1.0, 3.0, 3.0, 10.0] and out["s"].tolist() == ["a", "UNKNOWN", "UNKNOWN", "UNKNOWN"]
    assert out["d"].isna().sum() == 3 and rep == {"q": 1, "s": 3} and df["q"].isna().sum() == 1


def test_dedupe_customers():
    df = pd.DataFrame({"customer_id": ["C3", "C1", "C2", "C4", "C5"], "email": ["K@X.io ", "k@x.io", "", None, "d@x.io"],
                       "signup_date": pd.to_datetime(["2024-01-01", "2025-01-01", "2023-01-01", "2023-01-01", None])})
    out = nb.dedupe_customers(df)
    assert out["customer_id"].tolist() == ["C2", "C3", "C4", "C5"] and out.loc[out.customer_id == "C3", "email_norm"].item() == "k@x.io"


def test_parse_mixed_dates():
    s = pd.Series(["2025-03-04", "04/03/2025", " 31/12/2024 ", "2025-13-01", "yesterday", None, "12/31/2024"], index=list("abcdefg"))
    out = nb.parse_mixed_dates(s)
    assert list(out.index) == list("abcdefg") and out.dt.strftime("%Y-%m-%d").tolist()[:3] == ["2025-03-04", "2025-03-04", "2024-12-31"]
    assert out.iloc[3:].isna().all()


def test_clean_customers(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("Customer ID,Name,Email,Country,Signup Date,Segment,Is Active\n"
                 "C1,  pavan  KALYAN ,PK@x.io ,in,15/03/2024,smb,TRUE\n"
                 "C2,Pavan Kalyan,pk@x.io,IN,2024-05-01,smb,false\n"
                 "C3,Diya,diya.at.x.io,FI,2023-02-30,retail,true\n"
                 "C4,Erik,,SE,2022-01-01,retail,false\n")
    df, rep = nb.clean_customers(p)
    assert df["customer_id"].tolist() == ["C1", "C3", "C4"] and df.loc[0, "name"] == "Pavan Kalyan" and df.loc[0, "email"] == "pk@x.io"
    assert rep == {"rows_in": 4, "unparseable_dates": 1, "invalid_emails": 1, "missing_emails": 2, "duplicates_removed": 1, "rows_out": 3,
                   "countries": {"FI": 1, "IN": 1, "SE": 1}}
    assert df["is_active"].tolist() == [True, True, False]

def test_clean_customers_real():
    from pathlib import Path
    df, rep = nb.clean_customers(Path(__file__).resolve().parents[2] / "datasets/csv/customers.csv")
    assert rep["rows_in"] > 1000 and rep["duplicates_removed"] > 5 and rep["invalid_emails"] > 3 and df["country"].str.isupper().all()
