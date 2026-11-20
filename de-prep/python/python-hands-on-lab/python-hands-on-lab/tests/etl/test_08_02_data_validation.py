"""Tests for 08_data_engineering_python/02_data_validation.ipynb

Run: pytest tests/etl/test_08_02_data_validation.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/02_data_validation.ipynb")


def test_missing_fields():
    rec = {"a": 0, "b": False, "c": " ", "d": None, "e": "x", "f": []}
    assert nb.missing_fields(rec, ["a", "b", "c", "d", "e", "f", "g"]) == ["c", "d", "g"]


SCHEMA = {"id": "int", "price": "float", "active": "bool", "d": "date", "ts": "datetime", "name": "str"}

def test_type_errors_ok():
    assert nb.type_errors({"id": "1", "price": "2.5", "active": "Yes", "d": "2026-01-05", "ts": "2026-01-05T10:00:00Z", "name": "x"}, SCHEMA) == {}
    assert nb.type_errors({"id": "", "price": None}, SCHEMA) == {}

def test_type_errors_bad():
    errs = nb.type_errors({"id": "1.5", "price": "N/A", "active": "maybe", "d": "2026-13-01", "ts": "yesterday"}, SCHEMA)
    assert set(errs) == {"id", "price", "active", "d", "ts"} and errs["id"] == "expected int, got '1.5'"
    with pytest.raises(ValueError):
        nb.type_errors({}, {"x": "decimal"})


def test_evaluate_rules():
    recs = [{"id": i, "qty": q, "price": p} for i, (q, p) in enumerate([(1, "10"), (0, "5"), (3, "x"), (-1, "1"), (2, "2"), (0, "1"), (0, "1"), (0, "1"), (0, "1")])]
    rules = {"positive_qty": lambda r: r["qty"] > 0, "numeric_price": lambda r: float(r["price"]) >= 0}
    rep = nb.evaluate_rules(recs, rules, "id")
    assert rep["total"] == 9
    assert rep["rules"]["positive_qty"] == {"failed": 6, "failed_ids": [1, 3, 5, 6, 7], "pass_rate": 0.3333}
    assert rep["rules"]["numeric_price"]["failed"] == 1 and rep["rules"]["numeric_price"]["failed_ids"] == [2]
    assert nb.evaluate_rules([], rules, "id")["rules"]["positive_qty"]["pass_rate"] == 1.0


def test_validate_orders():
    from datetime import datetime as dt
    t1, t2 = dt(2026, 1, 1, 10), dt(2026, 1, 1, 12)
    base = {"customer_id": "C1", "product_id": "P1", "unit_price": 100.0, "order_ts": t1, "updated_at": t2, "status": "PLACED"}
    orders = [{"order_id": "ok", **base}, {"order_id": "a", **{**base, "customer_id": "C9", "product_id": "P9"}},
              {"order_id": "b", **{**base, "unit_price": 151.0}}, {"order_id": "c", **{**base, "unit_price": 50.0}},
              {"order_id": "d", **{**base, "updated_at": dt(2026, 1, 1, 9), "status": "DELIVERED", "unit_price": 0.0}}]
    assert nb.validate_orders(orders, {"C1"}, {"P1": 100.0}) == [
        ("a", ["unknown customer C9", "unknown product P9"]), ("b", ["price deviates 51% from catalog"]),
        ("d", ["price deviates 100% from catalog", "updated_at before order_ts", "delivered order with zero price"])]


SPEC = {"columns": {
    "order_id": {"type": "str", "required": True, "pattern": r"O\d{3}", "unique": True},
    "quantity": {"type": "int", "required": True, "min": 1, "max": 100},
    "price": {"type": "float", "min": 0},
    "status": {"type": "str", "required": True, "allowed": ["PLACED", "SHIPPED"], "normalize": "upper"},
    "order_date": {"type": "date", "min": "2026-01-01"},
    "ts": {"type": "datetime"},
    "gift": {"type": "bool"},
}}

def test_schema_validator():
    rows = [
        {"order_id": "O001", "quantity": "2", "price": "9.5", "status": "placed", "order_date": "2026-01-05", "ts": "2026-01-05T10:00:00Z", "gift": "yes", "junk": 1},
        {"order_id": "O001", "quantity": "1", "price": "", "status": "SHIPPED", "order_date": "", "ts": "", "gift": ""},
        {"order_id": "X1", "quantity": "0", "price": "-1", "status": "LOST", "order_date": "2025-12-31", "ts": "bad", "gift": "maybe"},
        {"order_id": "O002", "quantity": "abc", "status": " "},
        {"order_id": "O003", "quantity": "100", "status": "shipped", "price": None},
    ]
    valid, rejects, report = nb.SchemaValidator(SPEC).validate(rows)
    assert [v["order_id"] for v in valid] == ["O001", "O003"] and "junk" not in valid[0]
    from datetime import date
    assert valid[0]["quantity"] == 2 and valid[0]["gift"] is True and valid[0]["order_date"] == date(2026, 1, 5) and valid[0]["ts"].tzinfo is not None
    assert valid[1]["price"] is None and valid[1]["status"] == "SHIPPED"
    assert [r["row"] for r in rejects] == [2, 3, 4]
    assert rejects[0]["errors"] == ["order_id: duplicate value"]
    assert rejects[1]["errors"] == ["order_id: does not match pattern", "quantity: below min", "price: below min", "status: not in allowed values",
                                    "order_date: below min", "ts: invalid datetime", "gift: invalid bool"]
    assert rejects[2]["errors"] == ["quantity: invalid int", "status: required"]
    assert report["rows"] == 5 and report["valid"] == 2 and report["rejected"] == 3
    assert report["columns"]["price"]["nulls"] == 3 and report["columns"]["order_id"]["errors"] == 2
