"""Tests for 02_collections/02_tuples.ipynb

Run: pytest tests/collections/test_02_02_tuples.py -v
"""
import pytest

from labkit.testing import load

nb = load("02_collections/02_tuples.ipynb")


def test_summary_stats():
    assert nb.summary_stats([3, 1, 2]) == (3, 1, 3, 2.0)
    assert nb.summary_stats([2.5]) == (1, 2.5, 2.5, 2.5)
    assert nb.summary_stats([]) == (0, None, None, None)

def test_summary_stats_rounding():
    assert nb.summary_stats([1, 2, 2])[3] == 1.67


@pytest.mark.parametrize("uri, expected", [("s3://raw-bucket/sales/2026/01/part-0.csv", ("raw-bucket", "sales/2026/01/part-0.csv")),
                                           ("s3://bucket", ("bucket", "")), ("s3://bucket/", ("bucket", "")), ("s3://b/a//b", ("b", "a//b"))])
def test_split_s3_uri(uri, expected):
    assert nb.split_s3_uri(uri) == expected

@pytest.mark.parametrize("bad", ["https://x/y", "s3://", "s3:///key", "bucket/key"])
def test_split_s3_uri_invalid(bad):
    with pytest.raises(ValueError):
        nb.split_s3_uri(bad)


def test_txn_namedtuple():
    t = nb.Txn("T1", "A1", -1.0, "INR")
    assert isinstance(t, tuple) and t.is_debit() and t._fields == ("txn_id", "account", "amount", "currency")
    with pytest.raises(AttributeError):
        t.amount = 5
    tid, acct, amt, cur = t
    assert (tid, amt) == ("T1", -1.0)

def test_parse_txns():
    rows = [["T1", "A1", "-250.5", "inr"], ["T2", "A2", "N/A", "INR"], ["T3", "A1", "100", "usd"]]
    out = nb.parse_txns(rows)
    assert out == [nb.Txn("T1", "A1", -250.5, "INR"), nb.Txn("T3", "A1", 100.0, "USD")]
    assert {out[0], nb.Txn("T1", "A1", -250.5, "INR")} == {out[0]}


def test_daily_totals():
    txns = [{"account": "A2", "ts": "2026-01-05T10:00:00Z", "amount": 5.25, "status": "SUCCESS"},
            {"account": "A1", "ts": "2026-01-05T23:59:59Z", "amount": -10, "status": "SUCCESS"},
            {"account": "A1", "ts": "2026-01-05T01:00:00Z", "amount": 2.5, "status": "SUCCESS"},
            {"account": "A1", "ts": "2026-01-06T01:00:00Z", "amount": 99, "status": "FAILED"},
            {"account": "A1", "ts": "2026-01-04T01:00:00Z", "amount": 1, "status": "SUCCESS"}]
    result = nb.daily_totals(txns)
    assert result == {("A1", "2026-01-04"): 1.0, ("A1", "2026-01-05"): -7.5, ("A2", "2026-01-05"): 5.25}
    assert list(result) == sorted(result)

def test_daily_totals_empty():
    assert nb.daily_totals([]) == {}


def test_diff_snapshots():
    old = [("C1", "Kalyan", "Hyd"), ("C2", "Diya", "Pune"), ("C4", "Mia", "Oslo")]
    new = [("C4", "Mia", "Oslo"), ("C1", "Kalyan", "Vijayawada"), ("C3", "Erik", "Espoo")]
    ins, dele, upd = nb.diff_snapshots(old, new)
    assert ins == [("C3", "Erik", "Espoo")] and dele == [("C2", "Diya", "Pune")]
    assert upd == [(("C1", "Kalyan", "Hyd"), ("C1", "Kalyan", "Vijayawada"))]

def test_diff_snapshots_composite_key():
    old = [("A", 1, "x"), ("A", 2, "y")]
    new = [("A", 1, "x"), ("A", 2, "z"), ("B", 1, "q")]
    assert nb.diff_snapshots(old, new, key_len=2) == ([("B", 1, "q")], [], [(("A", 2, "y"), ("A", 2, "z"))])

def test_diff_snapshots_duplicates_and_empty():
    assert nb.diff_snapshots([], []) == ([], [], [])
    with pytest.raises(ValueError):
        nb.diff_snapshots([("A", 1), ("A", 2)], [])

def test_diff_snapshots_large():
    old = [(i, i % 7) for i in range(100_000)]
    new = [(i, i % 7 if i % 10 else -1) for i in range(1, 100_001)]
    ins, dele, upd = nb.diff_snapshots(old, new)
    assert len(ins) == 1 and len(dele) == 1 and len(upd) == 9_999
