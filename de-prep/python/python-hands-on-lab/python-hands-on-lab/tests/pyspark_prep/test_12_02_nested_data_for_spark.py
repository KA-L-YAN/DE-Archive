"""Tests for 12_pyspark_preparation/02_nested_data_for_spark.ipynb

Run: pytest tests/pyspark_prep/test_12_02_nested_data_for_spark.py -v
"""
import pytest

from labkit.testing import load

nb = load("12_pyspark_preparation/02_nested_data_for_spark.ipynb")


def test_explode():
    rows = [{"id": 1, "tags": ["a", "b"]}, {"id": 2, "tags": []}, {"id": 3, "tags": None}, {"id": 4}]
    assert nb.explode(rows, "tags", "tag") == [{"id": 1, "tag": "a"}, {"id": 1, "tag": "b"}]
    assert nb.explode(rows, "tags", "tag", outer=True) == [{"id": 1, "tag": "a"}, {"id": 1, "tag": "b"}, {"id": 2, "tag": None}, {"id": 3, "tag": None}, {"id": 4, "tag": None}]


def test_flatten_structs():
    row = {"id": 1, "customer": {"id": "C1", "contact": {"email": "x@y", "phone": None}}, "items": [{"p": 1}], "meta": {}}
    assert nb.flatten_structs(row) == {"id": 1, "customer_id": "C1", "customer_contact_email": "x@y", "customer_contact_phone": None, "items": [{"p": 1}], "meta": {}}
    with pytest.raises(ValueError):
        nb.flatten_structs({"a_b": 1, "a": {"b": 2}})


def test_collect_by():
    rows = [{"c": "A", "t": "x"}, {"c": "A", "t": "y"}, {"c": "B", "t": None}, {"c": "A", "t": "x"}, {"c": "B", "t": "z"}]
    assert nb.collect_by(rows, "c", "t") == {"A": ["x", "y", "x"], "B": ["z"]}
    assert nb.collect_by(rows, "c", "t", distinct=True) == {"A": ["x", "y"], "B": ["z"]}
    assert nb.collect_by([{"c": 1, "t": "b"}, {"c": 1, "t": "a"}], "c", "t", sort=True) == {1: ["a", "b"]}


def test_infer_schema():
    recs = [{"id": 1, "amount": 10, "tags": [], "customer": {"name": "a"}, "flag": True, "note": None},
            {"id": 2, "amount": 2.5, "tags": ["x"], "customer": {"name": "b", "age": 30}, "flag": "yes", "extra": [1, 2.0]}]
    assert nb.infer_schema(recs) == {"amount": "double", "customer": {"struct": {"age": "long", "name": "string"}}, "extra": {"array": "double"},
                                     "flag": "string", "id": "long", "note": "null", "tags": {"array": "string"}}

def test_infer_schema_real():
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[2] / "datasets/json/orders_nested.json").read_text())
    s = nb.infer_schema(data)
    assert s["id"] == "long" and s["items"]["array"]["struct"]["price"] == "double" and s["customer"]["struct"]["contact"]["struct"]["phone"] == "string"


def test_to_star_schema():
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[2] / "datasets/json/orders_nested.json").read_text())
    star = nb.to_star_schema(data)
    facts, dc, dp = star["fact_order_items"], star["dim_customer"], star["dim_product"]
    assert len(facts) == sum(len(o["items"]) for o in data) and len(star["fact_orders_without_items"]) == sum(1 for o in data if not o["items"])
    assert {f["customer_key"] for f in facts} <= {c["customer_key"] for c in dc} and {f["product_key"] for f in facts} <= {p["product_key"] for p in dp}
    assert len({c["customer_id"] for c in dc}) == len(dc) and [c["customer_key"] for c in dc] == list(range(1, len(dc) + 1))
    assert all(p["category"] for p in dp) and {f["payment_status"] for f in facts} >= {"captured", "unknown"}

def test_to_star_schema_latest_wins():
    orders = [{"id": 2, "created_at": "2026-01-02T00:00:00Z", "customer": {"id": "C1", "name": "New Name", "country": "IN"}, "items": [{"product_id": "P1", "name": "x", "category": None, "qty": 1, "price": 1.005}]},
              {"id": 1, "created_at": "2026-01-01T00:00:00Z", "customer": {"id": "C1", "name": "Old", "country": "IN"}, "items": [], "payment": {"status": "captured"}}]
    star = nb.to_star_schema(orders)
    assert star["dim_customer"] == [{"customer_key": 1, "customer_id": "C1", "name": "New Name", "country": "IN", "email": None}]
    assert star["dim_product"][0]["category"] == "UNKNOWN" and star["fact_orders_without_items"] == [1] and star["fact_order_items"][0]["payment_status"] == "unknown"
