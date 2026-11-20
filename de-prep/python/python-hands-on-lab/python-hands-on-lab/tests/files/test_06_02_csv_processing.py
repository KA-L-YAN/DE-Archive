"""Tests for 06_files_json_csv/02_csv_processing.ipynb

Run: pytest tests/files/test_06_02_csv_processing.py -v
"""
import pytest

from labkit.testing import load

nb = load("06_files_json_csv/02_csv_processing.ipynb")


def test_read_csv_bom_and_header(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(" id , name\n1,\"Kalyan, B\"\n2,Diya\n", encoding="utf-8-sig")
    assert nb.read_csv(p) == [{"id": "1", "name": "Kalyan, B"}, {"id": "2", "name": "Diya"}]
    e = tmp_path / "e.csv"; e.write_text("")
    assert nb.read_csv(e) == []

def test_read_csv_real_bom():
    from pathlib import Path
    rows = nb.read_csv(Path(__file__).resolve().parents[2] / "datasets/incoming/orders_03.csv")
    assert list(rows[0])[0] == "order_ts" and "coupon_code" in rows[0] and len(rows) > 380


def test_write_csv(tmp_path):
    out = tmp_path / "x" / "o.csv"
    n = nb.write_csv(out, [{"a": 1, "b": None}, {"b": "x,y", "c": 3}])
    assert n == 2 and out.read_text().splitlines() == ["a,b,c", "1,,", ',"x,y",3']

def test_write_csv_explicit_fields(tmp_path):
    out = tmp_path / "o.csv"
    nb.write_csv(out, [{"a": 1, "zzz": 9}], fieldnames=["a", "b"])
    assert out.read_text().splitlines() == ["a,b", "1,"]
    nb.write_csv(out, [], fieldnames=["a"])
    assert out.read_text().splitlines() == ["a"]


@pytest.mark.parametrize("sep", [",", ";", "|", "\t"])
def test_read_any_delimited(tmp_path, sep):
    p = tmp_path / "f.txt"
    p.write_text(sep.join(["id", "name", "city"]) + "\n" + sep.join(["1", "Kalyan", "Hyd"]) + "\n" + sep.join(["2", "Diya", "Pune"]) + "\n")
    d, rows = nb.read_any_delimited(p)
    assert d == sep and rows[1] == {"id": "2", "name": "Diya", "city": "Pune"}


def test_split_good_bad(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("id,name,amount\n1,a,10\n2,b\n\n,c,5\n4,d,abc\n5,\"multi\nline\",7\n6,x,1,EXTRA\n", encoding="utf-8")
    good, bad = nb.split_good_bad(p, required=["id"], numeric=["amount"])
    assert [g["id"] for g in good] == ["1", "5"] and good[1]["name"] == "multi\nline"
    assert [(b["line"], b["reason"]) for b in bad] == [(3, "expected 3 fields, got 2"), (5, "missing id"), (6, "non-numeric amount"),
                                                       (9, "expected 3 fields, got 4")]

def test_split_good_bad_real_corrupt():
    from pathlib import Path
    good, bad = nb.split_good_bad(Path(__file__).resolve().parents[2] / "datasets/incoming/corrupt.csv", ["order_id"], ["quantity", "unit_price"])
    assert len(good) == 1 and len(bad) == 3   # the unbalanced quote swallows the following line into one field


COLS = ["order_id", "customer_id", "quantity"]

def test_combine_incoming(tmp_path):
    inc = tmp_path / "in"; inc.mkdir()
    (inc / "orders_01.csv").write_text("order_id,customer_id,quantity\nO1,C1,1\nO2,C2\n", encoding="utf-8")
    (inc / "orders_02.csv").write_text("quantity,order_id,coupon,customer_id\n3,O3,NEW10,C3\n", encoding="utf-8-sig")
    (inc / "orders_03.csv.tmp").write_text("x"); (inc / "customers.json").write_text("[]")
    stats = nb.combine_incoming(inc, tmp_path / "out" / "all.csv", COLS)
    assert stats == {"files": ["orders_01.csv", "orders_02.csv"], "rows_written": 2, "rows_skipped": 1, "extra_columns": ["coupon"]}
    lines = (tmp_path / "out" / "all.csv").read_text().splitlines()
    assert lines == ["order_id,customer_id,quantity,coupon,source_file", "O1,C1,1,,orders_01.csv", "O3,C3,3,NEW10,orders_02.csv"]

def test_combine_incoming_real(tmp_path):
    from pathlib import Path
    cols = ["order_id", "customer_id", "product_id", "quantity", "unit_price", "order_ts", "status", "updated_at", "channel", "country"]
    stats = nb.combine_incoming(Path(__file__).resolve().parents[2] / "datasets/incoming", tmp_path / "c.csv", cols)
    assert stats["files"] == ["orders_01.csv", "orders_02.csv", "orders_03.csv"] and stats["extra_columns"] == ["coupon_code"]
    assert stats["rows_written"] > 1200
