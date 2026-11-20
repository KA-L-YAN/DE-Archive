"""Tests for 00_diagnostic/diagnostic_04_functions_oop.ipynb

Run: pytest tests/diagnostic/test_00_diagnostic_04_functions_oop.py -v
"""
import pytest

from labkit.testing import load

nb = load("00_diagnostic/diagnostic_04_functions_oop.ipynb")


def test_q1_make_accumulator():
    a, b = nb.make_accumulator(), nb.make_accumulator(100)
    assert [a(5), a(5), b(1), a(-10)] == [5, 10, 101, 0]


def test_q2_temperature():
    t = nb.Temperature(100)
    assert t.fahrenheit == 212 and repr(nb.Temperature(21.5)) == "Temperature(21.5°C)"
    t.fahrenheit = 32
    assert t.celsius == 0 and nb.Temperature(1) < nb.Temperature(2) and nb.Temperature(3) == nb.Temperature(3) and nb.Temperature(5) >= nb.Temperature(4)
    with pytest.raises(ValueError):
        nb.Temperature(-300)
    with pytest.raises(ValueError):
        t.fahrenheit = -1000


def test_q3_count_calls():
    @nb.count_calls
    def div(a, b=1):
        "divide"
        return a / b
    assert div(6, b=3) == 2 and div.__name__ == "div" and div.__doc__ == "divide"
    with pytest.raises(ZeroDivisionError):
        div(1, 0)
    assert div.calls == 2


def test_q4_inventory():
    inv = nb.Inventory()
    inv.add("SKU-2", 5); inv.add("SKU-1", 1)
    assert inv["SKU-2"] == 5 and inv["nope"] == 0 and "SKU-1" in inv and len(inv) == 2 and list(inv) == [("SKU-1", 1), ("SKU-2", 5)]
    inv.remove("SKU-1", 1)
    assert "SKU-1" not in inv
    with pytest.raises(ValueError):
        inv.remove("SKU-2", 6)
    with pytest.raises(ValueError):
        with inv.batch():
            inv.add("SKU-3", 9); inv.remove("SKU-2", 5); inv.remove("SKU-2", 1)
    assert list(inv) == [("SKU-2", 5)]
    with inv.batch():
        inv.add("SKU-3", 1)
    assert inv["SKU-3"] == 1
