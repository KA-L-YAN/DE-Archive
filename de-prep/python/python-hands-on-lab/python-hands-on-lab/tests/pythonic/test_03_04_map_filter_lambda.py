"""Tests for 03_pythonic_python/04_map_filter_lambda.ipynb

Run: pytest tests/pythonic/test_03_04_map_filter_lambda.py -v
"""
import pytest

from labkit.testing import load

nb = load("03_pythonic_python/04_map_filter_lambda.ipynb")


def test_apply_all():
    assert nb.apply_all("  Hyderabad ", [str.strip, str.upper, lambda s: s[:3]]) == "HYD"
    assert nb.apply_all(5, []) == 5
    assert nb.apply_all(2, [lambda x: x + 1, lambda x: x * 10]) == 30


ORDERS = [{"channel": "web", "status": "SHIPPED", "quantity": 3}, {"channel": "web", "status": "PLACED", "quantity": 5},
          {"channel": "app", "status": "SHIPPED", "quantity": 9}, {"channel": "web", "status": "DELIVERED", "quantity": 1}, {"status": "SHIPPED"}]

def test_where():
    pred = nb.where(channel="web", status={"SHIPPED", "DELIVERED"}, quantity=lambda q: q >= 2)
    assert list(filter(pred, ORDERS)) == [ORDERS[0]]
    assert len(list(filter(nb.where(), ORDERS))) == 5
    assert list(filter(nb.where(channel="we"), ORDERS)) == []
    assert len(list(filter(nb.where(status=("PLACED", "SHIPPED")), ORDERS))) == 4


def test_sort_by():
    rows = [{"country": "IN", "revenue": 10, "name": "b"}, {"country": "FI", "revenue": 5, "name": "a"},
            {"country": "IN", "revenue": 30, "name": "c"}, {"country": "IN", "revenue": 10, "name": "a"}]
    assert [(r["country"], r["name"]) for r in nb.sort_by(rows, "country", "-revenue", "name")] == [("FI", "a"), ("IN", "c"), ("IN", "a"), ("IN", "b")]
    assert [r["name"] for r in nb.sort_by(rows, "-name")] == ["c", "b", "a", "a"]
    assert nb.sort_by(rows) == rows and nb.sort_by([], "x") == []


def test_compose_and_pipe():
    inc, dbl = (lambda x: x + 1), (lambda x: x * 2)
    assert nb.compose(inc, dbl)(5) == 11 and nb.pipe(inc, dbl)(5) == 12
    assert nb.compose()(7) == 7 and nb.pipe()("x") == "x"
    clean = nb.pipe(str.strip, str.lower, lambda s: s.replace(" ", "_"))
    assert list(map(clean, ["  Order ID ", "AMOUNT"])) == ["order_id", "amount"]


ORD = [{"country": "IN", "order_id": 1, "quantity": 2}, {"country": "FI", "order_id": 2, "quantity": 1}, {"country": "IN", "order_id": 3, "quantity": 5}]

def test_group_reduce_sum():
    assert nb.group_reduce(ORD, "country", "quantity", lambda a, v: a + v, 0) == {"IN": 7, "FI": 1}

def test_group_reduce_collect_no_shared_state():
    r = nb.group_reduce(ORD, "country", "order_id", lambda a, v: (a.append(v) or a), [])
    assert r == {"IN": [1, 3], "FI": [2]}
    r2 = nb.group_reduce(ORD, lambda o: o["quantity"] > 1, "order_id", lambda a, v: a | {v}, set)
    assert r2 == {True: {1, 3}, False: {2}}

def test_group_reduce_max_and_order():
    r = nb.group_reduce(ORD, "country", "quantity", max, float("-inf"))
    assert list(r) == ["IN", "FI"] and r == {"IN": 5, "FI": 1}
