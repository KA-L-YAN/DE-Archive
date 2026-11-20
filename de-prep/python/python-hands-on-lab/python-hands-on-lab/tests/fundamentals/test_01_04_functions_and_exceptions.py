"""Tests for 01_python_fundamentals/04_functions_and_exceptions.ipynb

Run: pytest tests/fundamentals/test_01_04_functions_and_exceptions.py -v
"""
import pytest

from labkit.testing import load

nb = load("01_python_fundamentals/04_functions_and_exceptions.ipynb")


@pytest.mark.parametrize("value, expected", [(" 42 ", 42), ("-7", -7), (5, 5), ("+3", 3), ("0", 0)])
def test_safe_int_ok(value, expected):
    assert nb.safe_int(value) == expected

@pytest.mark.parametrize("value", [None, "", "  ", "3.5", "3.0", "abc", True, [1], 3.5])
def test_safe_int_default(value):
    assert nb.safe_int(value, default="D") == "D"


def test_validate_user_ok():
    assert nb.validate_user({"name": "Kalyan", "email": "k@x.io", "age": 23}) == []

def test_validate_user_all_errors():
    assert nb.validate_user({"email": "nope"}) == ["name is required", "email is invalid", "age must be an integer between 18 and 120"]

@pytest.mark.parametrize("age", [17, 121, "30", True, None, 30.0])
def test_validate_user_age(age):
    assert nb.validate_user({"name": "a", "email": "a@b", "age": age}) == ["age must be an integer between 18 and 120"]

def test_validate_user_blank_name():
    assert nb.validate_user({"name": "  ", "email": "a@b", "age": 18}) == ["name is required"]


def test_parse_records():
    good, bad = nb.parse_records(["1,Laptop,70000", "x,Mouse,10", "", "3,Desk", " 4 , Pen , 12.5 ", "5,A,abc"])
    assert good == [{"id": 1, "name": "Laptop", "amount": 70000.0}, {"id": 4, "name": "Pen", "amount": 12.5}]
    assert [n for n, _ in bad] == [2, 4, 6]
    assert all(isinstance(msg, str) and msg for _, msg in bad)

def test_parse_records_empty():
    assert nb.parse_records([]) == ([], [])


def test_record_validation_error_str():
    e = nb.RecordValidationError("quantity", "must be positive", -1)
    assert str(e) == "field 'quantity': must be positive (got -1)" and isinstance(e, ValueError)
    assert (e.field, e.message, e.value) == ("quantity", "must be positive", -1)
    assert str(nb.RecordValidationError("order_id", "is required")) == "field 'order_id': is required"

def test_validate_order_ok():
    assert nb.validate_order({"order_id": " O1 ", "quantity": "2", "unit_price": "10.5"}) == {"order_id": "O1", "quantity": 2, "unit_price": 10.5}

@pytest.mark.parametrize("order, field", [
    ({"quantity": 1, "unit_price": 1}, "order_id"), ({"order_id": "O", "quantity": "x", "unit_price": 1}, "quantity"),
    ({"order_id": "O", "quantity": 0, "unit_price": 1}, "quantity"), ({"order_id": "O", "quantity": 1, "unit_price": "N/A"}, "unit_price"),
    ({"order_id": "O", "quantity": 1, "unit_price": -2}, "unit_price"), ({"order_id": "O", "unit_price": 1}, "quantity"),
])
def test_validate_order_errors(order, field):
    with pytest.raises(nb.RecordValidationError) as info:
        nb.validate_order(order)
    assert info.value.field == field

def test_validate_order_chains_cause():
    with pytest.raises(nb.RecordValidationError) as info:
        nb.validate_order({"order_id": "O", "quantity": "two", "unit_price": 1})
    assert isinstance(info.value.__cause__, ValueError)


def test_process_batch_ok():
    r = nb.process_batch(["1", "x", "3"], int, max_failure_ratio=0.5)
    assert r["output"] == [1, 3] and r["processed"] == 2 and r["failed"] == 1
    assert r["errors"][0]["index"] == 1 and r["errors"][0]["error_type"] == "ValueError"

def test_process_batch_empty():
    assert nb.process_batch([], int) == {"output": [], "processed": 0, "failed": 0, "errors": []}

def test_process_batch_raises_with_summary():
    with pytest.raises(nb.BatchFailed) as info:
        nb.process_batch(["x", "y", "1"], int, max_failure_ratio=0.5)
    assert info.value.summary["failed"] == 2 and info.value.summary["output"] == [1]

def test_process_batch_boundary_ratio():
    assert nb.process_batch(["x", "1"], int, max_failure_ratio=0.5)["failed"] == 1

def test_process_batch_keyboard_interrupt_propagates():
    def boom(_):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        nb.process_batch([1], boom)
