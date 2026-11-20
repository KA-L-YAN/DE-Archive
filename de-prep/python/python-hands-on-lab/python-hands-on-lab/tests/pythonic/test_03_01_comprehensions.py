"""Tests for 03_pythonic_python/01_comprehensions.ipynb

Run: pytest tests/pythonic/test_03_01_comprehensions.py -v
"""
import pytest

from labkit.testing import load

nb = load("03_pythonic_python/01_comprehensions.ipynb")


def test_active_emails():
    users = [{"email": " A@X.io", "active": True}, {"email": "", "active": True}, {"email": "b@x.io", "active": False},
             {"active": True}, {"email": None, "active": 1}, {"email": "C@x.io ", "active": 1}]
    assert nb.active_emails(users) == ["a@x.io", "c@x.io"]
    assert nb.active_emails([]) == []


def test_price_map():
    rows = [{"product_id": "P1", "price": "10.5", "active": "true"}, {"product_id": "P2", "price": "x", "active": "true"},
            {"product_id": "P3", "price": "5", "active": "false"}, {"product_id": "P4", "price": "0", "active": "TRUE"},
            {"product_id": "P5", "price": "7", "active": "True"}, {"product_id": "P6", "price": None, "active": "true"}]
    assert nb.price_map(rows) == {"P1": 10.5, "P5": 7.0}

def test_to_float():
    assert nb.to_float("1.5") == 1.5 and nb.to_float("") is None and nb.to_float(None) is None


def test_categories_by_customer():
    orders = [{"customer": {"id": "C2"}, "items": [{"category": "Books"}, {"category": None}]},
              {"customer": {"id": "C1"}, "items": [{"category": "Home"}, {"category": "Books"}]},
              {"customer": {"id": "C2"}, "items": [{"category": "Books"}, {"category": "Grocery"}]},
              {"customer": {"id": "C3"}, "items": [{"category": None}]}, {"customer": {"id": "C4"}, "items": []}]
    assert nb.categories_by_customer(orders) == {"C1": ["Books", "Home"], "C2": ["Books", "Grocery"]}


def test_normalize():
    recs = [{"Order ID": "7", "amt": "1.5", "junk": 1}, {"Order ID": "x", "amt": ""}, {}]
    out = nb.normalize(recs, {"order_id": int, "amount": float, "note": str}, {"Order ID": "order_id", "amt": "amount"})
    assert out == [{"order_id": 7, "amount": 1.5, "note": None}, {"order_id": None, "amount": None, "note": None},
                   {"order_id": None, "amount": None, "note": None}]
    assert list(out[0]) == ["order_id", "amount", "note"]

def test_normalize_custom_callable():
    out = nb.normalize([{"d": "2026-01-05"}], {"d": lambda s: s.replace("-", "")})
    assert out == [{"d": "20260105"}]


ROWS = [{"c": "IN", "ch": "web", "q": 2}, {"c": "IN", "ch": "web", "q": 3}, {"c": "FI", "ch": "app", "q": 1}]

def test_pivot_sum():
    assert nb.pivot(ROWS, "c", "ch", "q") == {"FI": {"app": 1, "web": 0}, "IN": {"app": 0, "web": 5}}

def test_pivot_custom_agg_and_fill():
    assert nb.pivot(ROWS, "c", "ch", "q", agg=max, fill=None) == {"FI": {"app": 1, "web": None}, "IN": {"app": None, "web": 3}}
    assert nb.pivot(ROWS, "ch", "c", "q", agg=len) == {"app": {"FI": 1, "IN": 0}, "web": {"FI": 0, "IN": 2}}

def test_pivot_empty():
    assert nb.pivot([], "a", "b", "c") == {}
