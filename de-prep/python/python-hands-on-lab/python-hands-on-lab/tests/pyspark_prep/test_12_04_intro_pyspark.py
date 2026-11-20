"""Tests for 12_pyspark_preparation/04_intro_pyspark.ipynb

Run: pytest tests/pyspark_prep/test_12_04_intro_pyspark.py -v
"""
import pytest

from labkit.testing import load
pyspark = pytest.importorskip("pyspark")

@pytest.fixture(scope="module")
def spark():
    from pyspark.sql import SparkSession
    s = (SparkSession.builder.master("local[1]").appName("lab-tests").config("spark.sql.shuffle.partitions", "2")
         .config("spark.ui.enabled", "false").getOrCreate())
    yield s

nb = load("12_pyspark_preparation/04_intro_pyspark.ipynb")


def test_read_orders(spark):
    from pathlib import Path
    df = nb.read_orders(spark, Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv")
    assert dict(df.dtypes)["quantity"] == "int" and dict(df.dtypes)["unit_price"] == "double" and df.count() > 5000
    assert df.filter("unit_price IS NULL").count() > 10


def test_clean_orders(spark):
    rows = [("O1", "C1", "P1", 2, 10.0, "2026-01-05T10:00:00Z", "placed ", "2026-01-05T10:00:00Z", "WEB", "IN"),
            ("O1", "C1", "P1", 2, 10.0, "2026-01-05T10:00:00Z", "shipped", "2026-01-06T10:00:00Z", "web", "IN"),
            ("O2", "C2", "P1", 0, 10.0, "2026-01-05T10:00:00Z", "PLACED", "2026-01-05T10:00:00Z", "web", "IN"),
            ("O3", None, "P1", 1, 10.0, "2026-01-05T10:00:00Z", "PLACED", "2026-01-05T10:00:00Z", "web", "IN"),
            ("O4", "C4", "P1", 1, 3.333, "2026-01-05T10:00:00Z", "PLACED", "2026-01-05T10:00:00Z", "app", "FI")]
    cols = ["order_id", "customer_id", "product_id", "quantity", "unit_price", "order_ts", "status", "updated_at", "channel", "country"]
    out = {r["order_id"]: r for r in nb.clean_orders(spark.createDataFrame(rows, cols)).collect()}
    assert set(out) == {"O1", "O4"} and out["O1"]["status"] == "SHIPPED" and out["O1"]["channel"] == "web" and out["O4"]["amount"] == 3.33


def test_daily_revenue(spark):
    from datetime import datetime
    rows = [("O1", 2, 20.0, datetime(2026, 1, 5, 10), "SHIPPED", "IN"), ("O2", 1, 5.5, datetime(2026, 1, 5, 11), "PLACED", "IN"),
            ("O3", 1, 9.0, datetime(2026, 1, 5, 12), "CANCELLED", "IN"), ("O4", 3, 3.0, datetime(2026, 1, 6, 1), "PLACED", "FI")]
    df = spark.createDataFrame(rows, ["order_id", "quantity", "amount", "order_ts", "status", "country"])
    out = [r.asDict() for r in nb.daily_revenue(df).collect()]
    assert [(str(r["order_date"]), r["country"], r["orders"], r["units"], r["revenue"]) for r in out] == [("2026-01-05", "IN", 2, 3, 25.5), ("2026-01-06", "FI", 1, 3, 3.0)]


def test_write_daily(spark, tmp_path):
    from datetime import datetime
    cols = ["order_id", "order_ts", "amount"]
    day1 = spark.createDataFrame([("O1", datetime(2026, 1, 5, 10), 1.0), ("O2", datetime(2026, 1, 6, 10), 2.0)], cols)
    nb.write_daily(day1, tmp_path / "orders")
    rerun = spark.createDataFrame([("O3", datetime(2026, 1, 6, 12), 3.0)], cols)
    nb.write_daily(rerun, tmp_path / "orders")
    back = spark.read.parquet(str(tmp_path / "orders"))
    got = sorted((r["order_id"], str(r["order_date"])) for r in back.collect())
    assert got == [("O1", "2026-01-05"), ("O3", "2026-01-06")]
