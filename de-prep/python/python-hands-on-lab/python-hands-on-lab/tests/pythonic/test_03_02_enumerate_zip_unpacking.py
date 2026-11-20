"""Tests for 03_pythonic_python/02_enumerate_zip_unpacking.ipynb

Run: pytest tests/pythonic/test_03_02_enumerate_zip_unpacking.py -v
"""
import pytest

from labkit.testing import load

nb = load("03_pythonic_python/02_enumerate_zip_unpacking.ipynb")


def test_number_lines():
    assert nb.number_lines(["a", "b"] * 6)[:2] == ["01: a", "02: b"] and nb.number_lines(["a"] * 12)[-1] == "12: a"
    assert nb.number_lines(["x"], start=99) == ["99: x"] and nb.number_lines(["x", "y"], start=99) == ["099: x", "100: y"]
    assert nb.number_lines([]) == []


def test_rows_to_dicts():
    assert nb.rows_to_dicts(["a", "b"], [[1, 2], [3, 4]]) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert nb.rows_to_dicts(["a"], []) == []

@pytest.mark.parametrize("row", [[1], [1, 2, 3]])
def test_rows_to_dicts_strict(row):
    with pytest.raises(ValueError):
        nb.rows_to_dicts(["a", "b"], [row])


def test_reading_deltas():
    assert nb.reading_deltas([("t1", 10), ("t2", 15.5), ("t3", 2), ("t4", 2)]) == [("t2", 5.5), ("t3", 2), ("t4", 0)]
    assert nb.reading_deltas([]) == [] and nb.reading_deltas([("t", 1)]) == []
    assert nb.reading_deltas([("a", 0.1), ("b", 0.3)]) == [("b", 0.2)]


def test_to_columnar():
    assert nb.to_columnar([{"a": 1, "b": 2}, {"a": 3, "c": 4}]) == {"a": [1, 3], "b": [2, None], "c": [None, 4]}
    assert nb.to_columnar([]) == {}

def test_from_columnar_roundtrip():
    recs = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    assert nb.from_columnar(nb.to_columnar(recs)) == recs
    assert nb.from_columnar({}) == []

def test_from_columnar_unequal():
    with pytest.raises(ValueError):
        nb.from_columnar({"a": [1, 2], "b": [1]})


SPEC = [("acct", 6, str), ("_", 2, str), ("amount", 10, float), ("ccy", 3, str)]

def test_parse_fixed_width():
    out = nb.parse_fixed_width(["A00001  0000150.75INR", "A00002  -000020.00", "A00003            USD"], SPEC)
    assert out == [{"acct": "A00001", "amount": 150.75, "ccy": "INR"}, {"acct": "A00002", "amount": -20.0, "ccy": None},
                   {"acct": "A00003", "amount": None, "ccy": "USD"}]

def test_parse_fixed_width_too_long():
    with pytest.raises(ValueError, match="line 2"):
        nb.parse_fixed_width(["A", "A00001  0000150.75INRX"], SPEC)
