"""Tests for 04_java_to_python/01_collections_and_iteration.ipynb

Run: pytest tests/java_to_python/test_04_01_collections_and_iteration.py -v
"""
import pytest

from labkit.testing import load

nb = load("04_java_to_python/01_collections_and_iteration.ipynb")


def test_without_cancelled():
    orders = [{"status": "CANCELLED"}, {"status": "cancelled"}, {"status": "OK"}, {"status": "Cancelled"}, {"status": "SHIPPED"}]
    snapshot = list(orders)
    assert nb.without_cancelled(orders) == [{"status": "OK"}, {"status": "SHIPPED"}]
    assert orders == snapshot


def test_status_counts():
    orders = [{"status": s} for s in ["B", "A", "B", "C", "A", "B"]]
    r = nb.status_counts(orders)
    assert r == {"B": 3, "A": 2, "C": 1} and list(r) == ["B", "A", "C"]
    assert nb.status_counts([]) == {}


def test_group_by():
    items = [("C2", 1), ("C1", 2), ("C2", 3)]
    r = nb.group_by(items, key=lambda t: t[0])
    assert r == {"C2": [("C2", 1), ("C2", 3)], "C1": [("C1", 2)]} and list(r) == ["C2", "C1"]
    assert type(r) is dict and nb.group_by([], key=len) == {}
    assert nb.group_by(["aa", "b", "cc"], key=len) == {2: ["aa", "cc"], 1: ["b"]}


def test_lru_basic_eviction():
    c = nb.LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert "b" not in c and "a" in c and "c" in c and len(c) == 2

def test_lru_contains_does_not_refresh_and_stats():
    c = nb.LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert "a" in c
    c.put("c", 3)
    assert "a" not in c
    assert c.get("zzz", "dflt") == "dflt" and c.get("b") == 2
    assert (c.hits, c.misses) == (1, 1)

def test_lru_put_existing_refreshes():
    c = nb.LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("a", 10); c.put("c", 3)
    assert c.get("a") == 10 and "b" not in c

def test_lru_invalid():
    with pytest.raises(ValueError):
        nb.LRUCache(0)


RATES = {"USD": [("2026-02-01", 83.6), ("2026-01-01", 83.1)], "EUR": [("2026-01-15", 90.0)]}

def test_convert_to_inr():
    txns = [{"txn_id": "T1", "date": "2026-01-31", "amount": 10, "currency": "USD"},
            {"txn_id": "T2", "date": "2026-02-01", "amount": 10, "currency": "USD"},
            {"txn_id": "T3", "date": "2026-03-01", "amount": 2.5, "currency": "EUR"},
            {"txn_id": "T4", "date": "2020-01-01", "amount": 99, "currency": "INR"}]
    out = nb.convert_to_inr(txns, RATES)
    assert [o["inr_amount"] for o in out] == [831.0, 836.0, 225.0, 99.0]
    assert "inr_amount" not in txns[0]

@pytest.mark.parametrize("txn", [{"txn_id": "X", "date": "2026-01-14", "amount": 1, "currency": "EUR"},
                                 {"txn_id": "Y", "date": "2026-01-14", "amount": 1, "currency": "JPY"}])
def test_convert_to_inr_errors(txn):
    with pytest.raises(ValueError, match=txn["txn_id"]):
        nb.convert_to_inr([txn], RATES)

def test_convert_to_inr_large():
    rates = {"USD": [(f"2026-{m:02d}-01", 80 + m) for m in range(12, 0, -1)]}
    txns = [{"txn_id": i, "date": f"2026-{(i % 12) + 1:02d}-15", "amount": 1, "currency": "USD"} for i in range(100_000)]
    out = nb.convert_to_inr(txns, rates)
    assert out[0]["inr_amount"] == 81 and out[11]["inr_amount"] == 92
