"""Tests for 02_collections/05_nested_data.ipynb

Run: pytest tests/collections/test_02_05_nested_data.py -v
"""
import pytest

from labkit.testing import load

nb = load("02_collections/05_nested_data.ipynb")


ORDERS = [
    {"id": 101, "customer": "Pavan", "items": [{"name": "Laptop", "price": 70000}, {"name": "Mouse", "price": 1000}]},
    {"id": 102, "customer": "Diya", "items": [{"name": "Desk", "price": 12000, "qty": 1}, {"name": "Lamp", "price": 1500, "qty": 2}]},
    {"id": 103, "customer": "Pavan", "items": [{"name": "Coffee Beans", "price": 650, "qty": 4}]},
    {"id": 104, "customer": "Erik", "items": []},
]

def test_order_totals():
    assert nb.order_totals(ORDERS) == {101: 71000, 102: 15000, 103: 2600, 104: 0}
    assert nb.order_totals([]) == {}


def test_customer_ranking():
    r = nb.customer_ranking(ORDERS)
    assert [(c, n) for c, _, n in r] == [("Pavan", 2), ("Diya", 1), ("Erik", 1)]
    assert [s for _, s, _ in r] == [73600, 15000, 0]

def test_customer_ranking_tiebreak():
    o = [{"id": 1, "customer": "b", "items": [{"price": 5}]}, {"id": 2, "customer": "a", "items": [{"price": 5}]}]
    assert [c for c, _, _ in nb.customer_ranking(o)] == ["a", "b"]


def test_explode_items():
    rows = nb.explode_items(ORDERS)
    assert len(rows) == 6
    assert rows[1] == {"order_id": 101, "customer": "Pavan", "line_no": 2, "item": "Mouse", "price": 1000, "qty": 1, "line_total": 1000}
    assert rows[3]["line_total"] == 3000 and rows[3]["line_no"] == 2
    assert rows[-1] == {"order_id": 104, "customer": "Erik", "line_no": 0, "item": None, "price": None, "qty": None, "line_total": None}


def test_category_report_small():
    orders = [
        {"customer": {"country": "IN"}, "payment": {"status": "captured"}, "items": [{"category": "Books", "qty": 2, "price": 100}, {"category": None, "qty": 1, "price": 5}]},
        {"customer": {"country": "IN"}, "payment": {"status": "failed"}, "items": [{"category": "Books", "qty": 9, "price": 100}]},
        {"customer": {"country": "FI"}, "items": [{"category": "Home", "qty": 1, "price": 1}]},
        {"customer": {"country": "FI"}, "payment": {"status": "captured"}, "items": []},
    ]
    assert nb.category_report(orders) == {"IN": {"Books": 200.0, "UNKNOWN": 5.0}}

def test_category_report_real_file():
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[2] / "datasets/json/orders_nested.json").read_text())
    report = nb.category_report(data)
    assert set(report) <= {"IN", "US", "GB", "DE", "FI", "SE", "SG"} and list(report) == sorted(report)
    assert all(v > 0 for cats in report.values() for v in cats.values())


DOC = {"id": 1, "customer": {"contact": {"email": "p@x.io", "phone": None}}, "items": [{"name": "Laptop", "price": 0}, {"name": "Mouse"}]}

@pytest.mark.parametrize("path, expected", [("customer.contact.email", "p@x.io"), ("items.0.price", 0), ("items.-1.name", "Mouse"),
                                            ("items.5.name", "D"), ("customer.contact.phone", None), ("customer.contact.phone.x", "D"),
                                            ("items.x", "D"), ("id.x", "D"), ("nope", "D")])
def test_get_path(path, expected):
    assert nb.get_path(DOC, path, default="D") == expected

def test_project():
    rows = nb.project([DOC, {}], {"order_id": "id", "email": "customer.contact.email", "first_item": "items.0.name"})
    assert rows == [{"order_id": 1, "email": "p@x.io", "first_item": "Laptop"}, {"order_id": None, "email": None, "first_item": None}]
