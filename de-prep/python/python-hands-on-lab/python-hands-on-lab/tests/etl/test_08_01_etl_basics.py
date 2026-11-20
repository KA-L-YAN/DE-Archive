"""Tests for 08_data_engineering_python/01_etl_basics.ipynb

Run: pytest tests/etl/test_08_01_etl_basics.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/01_etl_basics.ipynb")


def test_extract(tmp_path):
    p = tmp_path / "o.csv"
    p.write_text("order_id,qty\nO1,1\n,\nO2,2\n", encoding="utf-8-sig")
    rows = list(nb.extract(p))
    assert rows == [{"order_id": "O1", "qty": "1", "_source": "o.csv", "_line": 2}, {"order_id": "O2", "qty": "2", "_source": "o.csv", "_line": 4}]


RAW = {"order_id": "O1", "customer_id": "C1", "product_id": "P1", "quantity": "2", "unit_price": "10.50", "order_ts": "2026-01-05T10:00:00Z", "status": "shipped", "updated_at": "2026-01-05T12:00:00Z", "channel": "WEB", "country": "IN"}

def test_transform_order_ok():
    r = nb.transform_order({**RAW, "_line": 7})
    assert (r["quantity"], r["unit_price"], r["amount"], r["status"], r["channel"], r["order_date"], r["_line"]) == (2, 10.5, 21.0, "SHIPPED", "web", "2026-01-05", 7)
    assert r["order_ts"].tzinfo is not None and r["updated_at"].hour == 12

@pytest.mark.parametrize("field, value, msg", [("quantity", "0", "quantity"), ("quantity", "-1", "quantity"), ("quantity", "two", "quantity"),
                                               ("unit_price", "N/A", "unit_price"), ("unit_price", "", "unit_price"), ("customer_id", "", "customer_id"),
                                               ("order_ts", "2026-13-01T10:00:00Z", "order_ts"), ("order_ts", "yesterday", "order_ts"), ("status", "LOST", "status")])
def test_transform_order_rejects(field, value, msg):
    with pytest.raises(ValueError, match=msg):
        nb.transform_order({**RAW, field: value})


def test_aggregate_daily():
    recs = [{"order_id": "O1", "order_date": "2026-01-02", "country": "IN", "quantity": 2, "amount": 10.25, "status": "SHIPPED"},
            {"order_id": "O1", "order_date": "2026-01-02", "country": "IN", "quantity": 1, "amount": 5.0, "status": "SHIPPED"},
            {"order_id": "O2", "order_date": "2026-01-01", "country": "IN", "quantity": 1, "amount": 3.0, "status": "PLACED"},
            {"order_id": "O3", "order_date": "2026-01-01", "country": "FI", "quantity": 9, "amount": 99.0, "status": "CANCELLED"},
            {"order_id": "O4", "order_date": "2026-01-01", "country": "FI", "quantity": 1, "amount": 1.0, "status": "DELIVERED"}]
    assert nb.aggregate_daily(iter(recs)) == [
        {"order_date": "2026-01-01", "country": "FI", "orders": 1, "units": 1, "revenue": 1.0},
        {"order_date": "2026-01-01", "country": "IN", "orders": 1, "units": 1, "revenue": 3.0},
        {"order_date": "2026-01-02", "country": "IN", "orders": 1, "units": 3, "revenue": 15.25}]


def test_run_etl(tmp_path):
    p = tmp_path / "orders.csv"
    p.write_text("order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"
                 "O1,C1,P1,2,10.5,2026-01-05T10:00:00Z,shipped,2026-01-05T12:00:00Z,WEB,in\n"
                 "O2,C1,P1,0,10.5,2026-01-05T10:00:00Z,PLACED,2026-01-05T12:00:00Z,web,IN\n"
                 "O3,C2,P2,1,5,2026-01-06T10:00:00Z,PLACED,2026-01-06T12:00:00Z,app,FI\n", encoding="utf-8")
    stats = nb.run_etl(p, tmp_path / "out")
    assert (stats["read"], stats["loaded"], stats["rejected"], stats["reject_ratio"]) == (3, 2, 1, 0.3333)
    import csv
    clean = list(csv.DictReader(open(tmp_path / "out" / "clean.csv")))
    rej = list(csv.DictReader(open(tmp_path / "out" / "rejected.csv")))
    summ = list(csv.DictReader(open(tmp_path / "out" / "daily_summary.csv")))
    assert [c["order_id"] for c in clean] == ["O1", "O3"] and clean[0]["order_ts"] == "2026-01-05T10:00:00Z" and clean[0]["country"] == "IN"
    assert rej[0]["order_id"] == "O2" and "quantity" in rej[0]["_error"] and len(summ) == 2

def test_run_etl_real(tmp_path):
    from pathlib import Path
    stats = nb.run_etl(Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv", tmp_path)
    assert stats["read"] == stats["loaded"] + stats["rejected"] and 0.02 < stats["reject_ratio"] < 0.1


HEADER = "order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"
def _row(i, qty=1):
    return f"O{i},C1,P1,{qty},2.5,2026-01-05T10:00:00Z,PLACED,2026-01-05T10:00:00Z,web,IN\n"

def test_run_multi_file_etl(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text(HEADER + "".join(_row(i) for i in range(5)) + _row(99, qty=0))
    b.write_text(HEADER + "".join(_row(i) for i in range(5, 8)))
    out = tmp_path / "out"
    m = nb.run_multi_file_etl([a, b], out, chunk_size=3)
    assert m["totals"] == {"read": 9, "loaded": 8, "rejected": 1}
    assert [p["path"] for p in m["parts"]] == ["clean/part-00000.csv", "clean/part-00001.csv", "clean/part-00002.csv"] and [p["rows"] for p in m["parts"]] == [3, 3, 2]
    assert (out / "_SUCCESS").exists() and (out / "rejected" / "a.csv").exists() and not (out / "rejected" / "b.csv").exists()
    import hashlib
    assert m["parts"][0]["sha256"] == hashlib.sha256((out / "clean/part-00000.csv").read_bytes()).hexdigest()
    m2 = nb.run_multi_file_etl([b], out, chunk_size=3)
    assert len(m2["parts"]) == 1 and sorted(p.name for p in (out / "clean").iterdir()) == ["part-00000.csv"]
