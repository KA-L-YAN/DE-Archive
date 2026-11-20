"""Tests for 02_collections/03_sets.ipynb

Run: pytest tests/collections/test_02_03_sets.py -v
"""
import pytest

from labkit.testing import load

nb = load("02_collections/03_sets.ipynb")


def test_unique_in_order():
    assert nb.unique_in_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
    assert nb.unique_in_order([]) == []
    assert nb.unique_in_order([1, 1, 1]) == [1]

def test_unique_in_order_large():
    data = list(range(50_000)) * 3
    assert nb.unique_in_order(data) == list(range(50_000))


def test_find_orphans():
    customers = [{"customer_id": "C1"}, {"customer_id": "C2"}]
    orders = [{"customer_id": "C1"}, {"customer_id": "C9"}, {"customer_id": ""}, {}, {"customer_id": "C9"}, {"customer_id": "C7"}]
    assert nb.find_orphans(orders, customers) == {"C9", "C7"}
    assert nb.find_orphans([], customers) == set()

def test_find_orphans_real_dataset():
    import csv
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "datasets/csv"
    with open(root / "orders.csv", newline="") as f1, open(root / "customers.csv", newline="") as f2:
        orphans = nb.find_orphans(list(csv.DictReader(f1)), list(csv.DictReader(f2)))
    assert orphans == {"C99999"}


def test_compare_columns():
    r = nb.compare_columns(["order_id", "amount", "status"], ["Order ID", " AMOUNT ", "coupon", "amount"])
    assert r == {"missing": ["status"], "unexpected": ["coupon"], "common": ["amount", "order_id"], "duplicated": ["amount"]}

def test_compare_columns_identical():
    assert nb.compare_columns(["a", "b"], ["b", "a"]) == {"missing": [], "unexpected": [], "common": ["a", "b"], "duplicated": []}


RP = {"viewer": {"orders:read", "customers:read"}, "ops": {"orders:*"}, "admin": {"orders:delete", "orders:write"}}

def test_effective_permissions():
    assert nb.effective_permissions(["viewer", "ops"], RP, {"orders:delete"}) == {"customers:read", "orders:read", "orders:write"}

def test_effective_permissions_deny_wildcard_and_unknown():
    assert nb.effective_permissions(["viewer", "ghost"], RP, {"orders:*"}) == {"customers:read"}
    assert nb.effective_permissions([], RP, set()) == set()

def test_effective_permissions_does_not_mutate():
    import copy
    before = copy.deepcopy(RP)
    nb.effective_permissions(["viewer", "ops", "admin"], RP, set())
    assert RP == before


def test_duplicate_groups():
    cs = [{"id": "1", "email": "K@x.io", "phone": None}, {"id": "2", "email": "k@x.io ", "phone": "+91 98765-43210"},
          {"id": "3", "email": None, "phone": "9876543210"}, {"id": "4", "email": "other@x.io", "phone": ""},
          {"id": "5", "email": "", "phone": "123"}, {"id": "6", "email": "", "phone": "1234"}]
    assert nb.duplicate_groups(cs) == [["1", "2", "3"]]

def test_duplicate_groups_multiple_sorted():
    cs = [{"id": "b", "email": "z@z"}, {"id": "a", "email": "z@z"}, {"id": "d", "email": "y@y"}, {"id": "c", "email": "y@y"}]
    assert nb.duplicate_groups(cs) == [["a", "b"], ["c", "d"]]

def test_duplicate_groups_large():
    cs = [{"id": f"{i:06d}", "email": f"u{i // 2}@x.io", "phone": None} for i in range(20_000)]
    groups = nb.duplicate_groups(cs)
    assert len(groups) == 10_000 and all(len(g) == 2 for g in groups)
