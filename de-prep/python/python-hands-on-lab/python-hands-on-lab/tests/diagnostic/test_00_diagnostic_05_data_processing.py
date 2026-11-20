"""Tests for 00_diagnostic/diagnostic_05_data_processing.ipynb

Run: pytest tests/diagnostic/test_00_diagnostic_05_data_processing.py -v
"""
import pytest

from labkit.testing import load

nb = load("00_diagnostic/diagnostic_05_data_processing.ipynb")


def test_q1_totals_by_category(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text('sku,category,amount\nA,books,10.5\nB,home,x\nC,books,"1,5"\nD,home,4\nE,books,0.25\n')
    assert nb.totals_by_category(p) == {"books": 10.75, "home": 4.0}


def test_q2_clean():
    recs = [{"email": " K@X.IO ", "country": "in", "age": "23"}, {"email": "nope", "age": 5}, {"email": "a@b", "age": "x"}, {"email": "a@b", "age": 200}]
    good, bad = nb.clean(recs)
    assert good == [{"email": "k@x.io", "country": "IN", "age": 23}] and [b["reason"] for b in bad] == ["bad email", "bad age", "age out of range"]
    assert recs[0]["email"] == " K@X.IO "


def test_q3_latest_by_key():
    recs = [{"id": "b", "ts": "2026-01-02", "v": 1}, {"id": "a", "ts": "2026-01-01", "v": 2}, {"id": "b", "ts": "2026-01-03", "v": 3}, {"id": "b", "ts": "2026-01-03", "v": 4}]
    assert [r["v"] for r in nb.latest_by_key(recs, "id", "ts")] == [2, 4]


def test_q4_mini_etl(tmp_path):
    import json
    lines = [json.dumps({"order_id": "O1", "customer": "k", "amount": 10, "status": "PAID", "ts": "2026-01-01"}),
             json.dumps({"order_id": "O1", "customer": "k", "amount": 12.5, "status": "PAID", "ts": "2026-01-02"}),
             json.dumps({"order_id": "O2", "customer": "d", "amount": 7, "status": "REFUNDED", "ts": "2026-01-01"}),
             json.dumps({"order_id": "O3", "customer": "d", "amount": -1, "status": "PAID", "ts": "2026-01-01"}),
             json.dumps({"order_id": "O4", "customer": "e", "amount": True, "status": "PAID", "ts": "2026-01-01"}),
             '{"order_id": "O5", ', "", "[1, 2]",
             json.dumps({"order_id": "O6", "customer": "d", "amount": 2.25, "status": "PAID", "ts": "2026-01-03"})]
    src = tmp_path / "in.jsonl"; src.write_text("\n".join(lines))
    s = nb.mini_etl(src, tmp_path / "out" / "summary.json")
    assert s == {"lines": 8, "malformed": 2, "invalid": 2, "duplicates": 1, "orders": 3, "revenue": 14.75, "by_customer": {"d": 2.25, "k": 12.5}}
    assert json.loads((tmp_path / "out" / "summary.json").read_text()) == s
