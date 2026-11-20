"""Tests for 04_java_to_python/02_streams_vs_python.ipynb

Run: pytest tests/java_to_python/test_04_02_streams_vs_python.py -v
"""
import pytest

from labkit.testing import load

nb = load("04_java_to_python/02_streams_vs_python.ipynb")


def test_big_spender_names():
    cs = [{"name": "Zed", "spend": 100}, {"name": "Amy", "spend": 500}, {"name": "Bob", "spend": 300}, {"name": "Cy", "spend": 300.01}]
    assert nb.big_spender_names(cs, 300) == ["Amy", "Cy"]
    assert nb.big_spender_names([], 0) == []


def test_revenue_by_category():
    lines = [{"category": "b", "qty": 2, "price": 1.25}, {"category": "a", "qty": 1, "price": 10}, {"category": "b", "qty": 1, "price": 0.1}]
    r = nb.revenue_by_category(lines)
    assert r == {"a": 10.0, "b": 2.6} and list(r) == ["a", "b"]


def test_partition():
    assert nb.partition(range(7), lambda x: x % 3 == 0) == ([0, 3, 6], [1, 2, 4, 5])
    assert nb.partition([], bool) == ([], [])

def test_partition_single_pass():
    calls = []
    def pred(x):
        calls.append(x); return x > 1
    gen = (i for i in range(4))
    assert nb.partition(gen, pred) == ([2, 3], [0, 1]) and calls == [0, 1, 2, 3]


def test_top_tags():
    orders = [{"tags": ["Gift", "gift", "prime"]}, {"tags": ["prime", "bulk"]}, {"tags": None}, {}, {"tags": ["festive", "PRIME"]}, {"tags": ["bulk"]}]
    assert nb.top_tags(orders) == [("prime", 3), ("bulk", 2), ("festive", 1)]
    assert nb.top_tags(orders, n=10)[-1] == ("gift", 1) and nb.top_tags([]) == []


def test_country_summary():
    orders = iter([{"order_id": "a", "country": "IN", "amount": 10.0}, {"order_id": "b", "country": "FI", "amount": 5.0},
                   {"order_id": "c", "country": "IN", "amount": 30.0}, {"order_id": "d", "country": "IN", "amount": 30.0}])
    assert nb.country_summary(orders) == {"FI": {"count": 1, "total": 5.0, "avg": 5.0, "max_order_id": "b"},
                                          "IN": {"count": 3, "total": 70.0, "avg": 23.33, "max_order_id": "c"}}
    assert nb.country_summary(iter([])) == {}

def test_country_summary_real_csv():
    import csv
    from pathlib import Path
    def rows():
        with open(Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    yield {"order_id": r["order_id"], "country": r["country"], "amount": int(r["quantity"]) * float(r["unit_price"])}
                except ValueError:
                    continue
    summary = nb.country_summary(rows())
    assert sum(s["count"] for s in summary.values()) > 4500 and list(summary) == sorted(summary)
