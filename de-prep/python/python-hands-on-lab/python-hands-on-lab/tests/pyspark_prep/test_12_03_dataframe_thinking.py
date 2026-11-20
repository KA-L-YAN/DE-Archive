"""Tests for 12_pyspark_preparation/03_dataframe_thinking.ipynb

Run: pytest tests/pyspark_prep/test_12_03_dataframe_thinking.py -v
"""
import pytest

from labkit.testing import load
import pandas as pd

nb = load("12_pyspark_preparation/03_dataframe_thinking.ipynb")


def test_country_report():
    orders = [{"country": "IN", "status": "SHIPPED", "amount": 10.0}, {"country": "IN", "status": None, "amount": 99.0}, {"country": "IN", "status": "PLACED", "amount": 5.0},
              {"country": "FI", "status": "SHIPPED", "amount": 50.0}, {"country": "SE", "status": "PLACED", "amount": 1.0}, {"country": "SE", "status": "PLACED", "amount": 14.0},
              {"country": "FI", "status": "CANCELLED", "amount": 1.0}]
    assert nb.country_report(orders) == [("IN", 2, 15.0), ("SE", 2, 15.0)]


def test_country_report_pd():
    df = pd.DataFrame({"country": ["IN", "IN", "IN", "FI", "SE", "SE", "FI"], "status": ["SHIPPED", None, "PLACED", "SHIPPED", "PLACED", "PLACED", "CANCELLED"],
                       "amount": [10.0, 99.0, 5.0, 50.0, 1.0, 14.0, 1.0]})
    assert nb.country_report_pd(df).to_dict("records") == [{"country": "IN", "n": 2, "total": 15.0}, {"country": "SE", "n": 2, "total": 15.0}]


def test_three_valued_logic():
    assert nb.sql_eq(None, None) is None and nb.sql_eq(1, 1) is True and nb.sql_eq(1, None) is None
    assert nb.sql_and(False, None) is False and nb.sql_and(True, None) is None and nb.sql_and(True, True) is True
    assert nb.sql_or(True, None) is True and nb.sql_or(False, None) is None and nb.sql_or(False, False) is False

def test_null_aggregates():
    vals = [10, None, 20, None]
    assert nb.sql_count(vals) == 2 and nb.sql_count(vals, star=True) == 4 and nb.sql_avg(vals) == 15 and nb.sql_avg([None]) is None and nb.sql_count([]) == 0


PATHS = [f"sales/dt=2026-01-0{d}/country={c}/part-0.parquet" for d in range(1, 6) for c in ("IN", "FI", "SE")] + ["sales/_unpartitioned/part-0.parquet"]

def test_prune():
    keep, skipped = nb.prune(PATHS, {"dt": (">=", "2026-01-04"), "country": ("in", {"IN", "FI"})})
    assert keep == ["sales/dt=2026-01-04/country=IN/part-0.parquet", "sales/dt=2026-01-04/country=FI/part-0.parquet",
                    "sales/dt=2026-01-05/country=IN/part-0.parquet", "sales/dt=2026-01-05/country=FI/part-0.parquet", "sales/_unpartitioned/part-0.parquet"]
    assert skipped == 11
    assert nb.prune(PATHS, {})[1] == 0 and nb.prune(PATHS, {"country": ("!=", "SE")})[1] == 5
    with pytest.raises(ValueError):
        nb.prune(PATHS, {"dt": ("like", "2026%")})


def test_lazy_frame(tmp_path):
    p = tmp_path / "o.csv"
    p.write_text("order_id,customer_id,quantity,unit_price,status,country,notes\n"
                 "O1,C1,2,10.0,SHIPPED,IN,a\nO2,C2,1,5.0,PLACED,FI,b\nO3,C1,5,1.0,SHIPPED,IN,c\nO4,C3,x,1.0,SHIPPED,IN,d\n")
    lf = (nb.LazyFrame.read_csv(p)
            .with_column("amount", lambda r: int(r["quantity"]) * float(r["unit_price"]), depends_on=["quantity", "unit_price"])
            .filter("status", "=", "SHIPPED").filter("quantity", ">", 1).filter("amount", ">", 6.0)
            .select("order_id", "amount"))
    plan = lf.explain().splitlines()
    assert plan[0] == "Scan csv [order_id, quantity, status, unit_price] filters=[status = 'SHIPPED', quantity > 1]"
    assert plan[1:] == ["WithColumn amount <- ['quantity', 'unit_price']", "Filter amount > 6.0", "Select ['order_id', 'amount']"]
    assert lf.collect() == [{"order_id": "O1", "amount": 20.0}]
    assert lf.last_scan_stats == {"rows_read": 4, "rows_after_scan_filters": 2, "columns_read": 4}

def test_lazy_frame_no_select_reads_all(tmp_path):
    p = tmp_path / "o.csv"; p.write_text("a,b\n1,x\n2,y\n")
    lf = nb.LazyFrame.read_csv(p).filter("a", ">=", 2)
    assert lf.collect() == [{"a": "2", "b": "y"}] and lf.explain().startswith("Scan csv [*]") and lf.last_scan_stats["columns_read"] == 2
