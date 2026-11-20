"""Tests for 02_collections/04_dictionaries.ipynb

Run: pytest tests/collections/test_02_04_dictionaries.py -v
"""
import pytest

from labkit.testing import load

nb = load("02_collections/04_dictionaries.ipynb")


def test_index_by():
    rs = [{"id": 1, "n": "a"}, {"id": 2, "n": "b"}]
    assert nb.index_by(rs, "id") == {1: rs[0], 2: rs[1]}
    assert nb.index_by([], "id") == {}

def test_index_by_errors():
    with pytest.raises(ValueError):
        nb.index_by([{"id": 1}, {"id": 1}], "id")
    with pytest.raises(KeyError):
        nb.index_by([{"x": 1}], "id")


def test_invert():
    assert nb.invert({"data": ["kalyan", "diya"], "platform": ["kalyan", "kalyan"]}) == {"diya": ["data"], "kalyan": ["data", "platform"]}
    assert nb.invert({}) == {} and nb.invert({"x": []}) == {}


def test_revenue_by():
    orders = [{"channel": "web", "quantity": "2", "unit_price": "10.5"}, {"channel": "app", "quantity": "1", "unit_price": "100"},
              {"channel": "web", "quantity": "0", "unit_price": "5"}, {"channel": "web", "quantity": "1", "unit_price": "N/A"},
              {"channel": "store", "quantity": "3", "unit_price": "1"}, {"channel": "web", "quantity": "1", "unit_price": "0.25"}]
    r = nb.revenue_by(orders, "channel")
    assert r == {"app": 100.0, "web": 21.25, "store": 3.0}
    assert list(r) == ["app", "web", "store"]

def test_revenue_by_empty():
    assert nb.revenue_by([], "x") == {}


def test_deep_merge():
    base = {"db": {"host": "localhost", "port": 5432, "opts": {"ssl": False}}, "tags": ["a"], "debug": True}
    over = {"db": {"host": "prod", "opts": {"ssl": True}}, "tags": ["b"], "debug": None, "new": 1}
    assert nb.deep_merge(base, over) == {"db": {"host": "prod", "port": 5432, "opts": {"ssl": True}}, "tags": ["b"], "new": 1}

def test_deep_merge_no_mutation_no_sharing():
    base, over = {"a": {"b": [1]}}, {"c": {"d": [2]}}
    merged = nb.deep_merge(base, over)
    merged["a"]["b"].append(99); merged["c"]["d"].append(99)
    assert base == {"a": {"b": [1]}} and over == {"c": {"d": [2]}}

def test_deep_merge_type_change():
    assert nb.deep_merge({"a": {"x": 1}}, {"a": 5}) == {"a": 5}
    assert nb.deep_merge({"a": 5}, {"a": {"x": 1}}) == {"a": {"x": 1}}


DOC = {"id": 1, "customer": {"name": "Pavan", "contact": {"email": "p@x.io"}}, "items": [{"name": "Laptop", "price": 70000}, {"name": "Mouse", "price": 1000}],
       "tags": [], "meta": {}, "matrix": [[1, 2], [3]]}

def test_flatten_dict():
    flat = nb.flatten_dict(DOC)
    assert flat["customer.contact.email"] == "p@x.io" and flat["items.1.price"] == 1000
    assert flat["tags"] == [] and flat["meta"] == {} and flat["matrix.0.1"] == 2 and flat["id"] == 1

def test_roundtrip():
    assert nb.unflatten_dict(nb.flatten_dict(DOC)) == DOC

def test_unflatten_non_consecutive_stays_dict():
    assert nb.unflatten_dict({"a.0": "x", "a.2": "y"}) == {"a": {"0": "x", "2": "y"}}

def test_custom_sep():
    assert nb.flatten_dict({"a": {"b": 1}}, sep="__") == {"a__b": 1}
    assert nb.unflatten_dict({"a__b": 1}, sep="__") == {"a": {"b": 1}}
