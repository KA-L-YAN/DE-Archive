"""Tests for 00_diagnostic/diagnostic_02_collections.ipynb

Run: pytest tests/diagnostic/test_00_diagnostic_02_collections.py -v
"""
import pytest

from labkit.testing import load

nb = load("00_diagnostic/diagnostic_02_collections.ipynb")


def test_q1_inverted_index():
    assert nb.inverted_index({"d2": "Spark is fast", "d1": "python is FUN fun"}) == {"fast": ["d2"], "fun": ["d1"], "is": ["d1", "d2"], "python": ["d1"], "spark": ["d2"]}
    assert nb.inverted_index({}) == {}


def test_q2_top_k():
    assert nb.top_k(["b", "a", "c", "b", "a", "d"], 3) == [("a", 2), ("b", 2), ("c", 1)] and nb.top_k([], 2) == [] and nb.top_k(["x"], 5) == [("x", 1)]


def test_q3_merge_intervals():
    assert nb.merge_intervals([(8, 10), (1, 3), (2, 6), (15, 18), (6, 7), (16, 17)]) == [(1, 7), (8, 10), (15, 18)]
    assert nb.merge_intervals([]) == [] and nb.merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]


def test_q4_customer_summary():
    orders = [{"id": 1, "customer": "Pavan", "status": "PAID", "items": [{"name": "Laptop", "price": 70000}, {"name": "Mouse", "price": 1000, "qty": 2}]},
              {"id": 2, "customer": "Diya", "status": "REFUNDED", "items": [{"name": "Desk", "price": 12000}]},
              {"id": 3, "customer": "Pavan", "status": "PAID", "items": [{"name": "Mouse", "price": 1000, "qty": 3}]},
              {"id": 4, "customer": "Erik", "status": "PAID", "items": [{"name": "b", "price": 5}, {"name": "a", "price": 5}]}]
    assert nb.customer_summary(orders) == {"Diya": {"orders": 1, "items": 1, "spend": 0, "top_item": None},
                                           "Erik": {"orders": 1, "items": 2, "spend": 10, "top_item": "a"},
                                           "Pavan": {"orders": 2, "items": 6, "spend": 75000, "top_item": "Laptop"}}
