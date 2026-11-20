"""Tests for 04_java_to_python/04_interfaces_vs_duck_typing.ipynb

Run: pytest tests/java_to_python/test_04_04_interfaces_vs_duck_typing.py -v
"""
import pytest

from labkit.testing import load
from decimal import Decimal

nb = load("04_java_to_python/04_interfaces_vs_duck_typing.ipynb")


def test_total_size():
    class S3Obj:
        def size(self): return 10
    class LocalFile:
        def __init__(self, n): self.n = n
        def size(self): return self.n
    class NoSize: pass
    class SizeAttr:
        size = 99
    assert nb.total_size([S3Obj(), LocalFile(5), NoSize(), SizeAttr()]) == 15 and nb.total_size([]) == 0


def test_list_sink():
    s = nb.ListSink()
    assert nb.run_export([{"a": i} for i in range(5)], s) == 5 and s.rows == [{"a": i} for i in range(5)]

def test_csv_sink_header_once(tmp_path):
    p = tmp_path / "out.csv"
    s = nb.CsvSink(p, ["a", "b"])
    assert nb.run_export([{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}], s, batch_size=2) == 3
    assert p.read_text().splitlines() == ["a,b", "1,2", "3,4", "5,6"]

def test_any_object_with_write_works():
    class CountingSink:
        def __init__(self): self.calls = 0
        def write(self, records):
            self.calls += 1
            return len(records)
    s = CountingSink()
    assert nb.run_export(range(0), s) == 0
    assert nb.run_export([1, 2, 3], s, batch_size=1) == 3 and s.calls == 3


def test_validator_abc():
    with pytest.raises(TypeError):
        nb.Validator()
    class Incomplete(nb.Validator):
        pass
    with pytest.raises(TypeError):
        Incomplete()

def test_validators():
    vs = [nb.RequiredFields("id", "email"), nb.RangeCheck("qty", 1, 100), lambda r: ["custom"] if r.get("flag") else []]
    assert nb.validate_all({"id": 1, "email": "a@b", "qty": 5}, vs) == []
    assert nb.validate_all({"id": " ", "qty": "500", "flag": 1}, vs) == ["id is required", "email is required", "qty out of range [1, 100]", "custom"]
    assert nb.validate_all({"id": 1, "email": "x", "qty": "abc"}, vs) == ["qty is not numeric"]
    assert nb.RangeCheck("q", 0, 1)({"q": 0}) == []


def test_money_arithmetic():
    a, b = nb.Money("10.50", "inr"), nb.Money(2, "INR")
    assert a + b == nb.Money("12.50", "INR") and a - b == nb.Money("8.5", "INR") and a * 2 == nb.Money("21", "INR") and 3 * b == nb.Money(6, "INR")
    assert sum([a, b]) == nb.Money("12.5", "INR") and sum([a], start=nb.Money("0", "INR")) == a

def test_money_compare_hash_repr():
    a, b = nb.Money("10.50", "INR"), nb.Money("10.5", "INR")
    assert a == b and len({a, b}) == 1 and nb.Money(1, "INR") < a <= b and a >= nb.Money(3, "INR")
    assert repr(nb.Money("10.50", "INR")) == "Money('10.50', 'INR')" and str(nb.Money("7", "usd")) == "USD 7.00"
    assert a != "10.50"

def test_money_errors():
    with pytest.raises(TypeError):
        nb.Money(0.1, "INR")
    with pytest.raises(ValueError):
        nb.Money(1, "INR") + nb.Money(1, "USD")
    with pytest.raises(TypeError):
        nb.Money(1, "INR") + 5
    with pytest.raises(AttributeError):
        nb.Money(1, "INR").amount = Decimal(2)


def test_percent_off_and_names():
    s = nb.percent_off(10, min_total=1000)
    assert s({"total": 2000}) == 200 and s({"total": 999}) == 0 and s.__name__ == "percent_off_10"

def test_tiered():
    t = nb.TieredDiscount([(5000, 500), (1000, 50), (2000, 150)])
    assert [t({"total": x}) for x in (999, 1000, 1999, 2500, 10_000)] == [0, 50, 50, 150, 500]

def test_best_price():
    strategies = [nb.percent_off(10, min_total=1000), nb.TieredDiscount([(1000, 50), (2000, 300)]), lambda o: 5]
    assert nb.best_price({"total": 2500}, strategies) == (2200.0, "TieredDiscount")
    assert nb.best_price({"total": 4000}, strategies) == (3600.0, "percent_off_10")
    assert nb.best_price({"total": 100}, strategies) == (95.0, "<lambda>")
    assert nb.best_price({"total": 100}, []) == (100, "none")
    assert nb.best_price({"total": 30}, [nb.TieredDiscount([(10, 50)])]) == (0, "TieredDiscount")
