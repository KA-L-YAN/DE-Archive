"""Tests for 04_java_to_python/03_classes_properties_optional.ipynb

Run: pytest tests/java_to_python/test_04_03_classes_properties_optional.py -v
"""
import pytest

from labkit.testing import load

nb = load("04_java_to_python/03_classes_properties_optional.ipynb")


def test_customer_dataclass():
    a = nb.Customer("C1", "Kalyan")
    b = nb.Customer("C1", "Kalyan")
    assert a == b and a.email is None and a.tags == []
    a.tags.append("vip")
    assert b.tags == [] and "Kalyan" in repr(a)
    assert a.display_name() == "Kalyan"
    assert nb.Customer("C2", "Diya", email="d@x.io").display_name() == "Diya <d@x.io>"


def test_account():
    a = nb.Account("A1", "  Kalyan@X.IO ")
    assert a.email == "kalyan@x.io" and a.balance == 0.0
    assert a.deposit(100) == 100 and a.withdraw(30) == 70
    with pytest.raises(AttributeError):
        a.balance = 1_000_000
    with pytest.raises(ValueError, match="insufficient"):
        a.withdraw(71)
    with pytest.raises(ValueError):
        a.deposit(0)
    with pytest.raises(ValueError):
        a.email = "nope"
    with pytest.raises(ValueError):
        nb.Account("A2", "bad")


CS = [{"customer_id": "C1", "address": {"city": " Hyderabad "}}, {"customer_id": "C2", "address": None},
      {"customer_id": "C3", "address": {"city": "   "}}, {"customer_id": "C4"}, {"customer_id": "C1", "address": {"city": "dup"}}]

def test_find_customer():
    assert nb.find_customer(CS, "C1")["address"]["city"] == " Hyderabad " and nb.find_customer(CS, "C9") is None

@pytest.mark.parametrize("cid, expected", [("C1", "Hyderabad"), ("C2", "UNKNOWN"), ("C3", "UNKNOWN"), ("C4", "UNKNOWN"), ("C9", "UNKNOWN")])
def test_customer_city(cid, expected):
    assert nb.customer_city(CS, cid) == expected

def test_customer_city_custom_default():
    assert nb.customer_city(CS, "C9", default=None) is None


def test_job_config_defaults_and_frozen():
    import dataclasses
    c = nb.JobConfig("daily", "in/", "out/")
    assert (c.batch_size, c.max_retries, c.dry_run, c.tags) == (1000, 3, False, ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.batch_size = 5
    assert hash(c) == hash(nb.JobConfig("daily", "in/", "out/"))

@pytest.mark.parametrize("kw", [dict(name=" "), dict(batch_size=0), dict(max_retries=11), dict(output_path="in/")])
def test_job_config_validation(kw):
    base = dict(name="daily", input_path="in/", output_path="out/")
    with pytest.raises(ValueError):
        nb.JobConfig(**{**base, **kw})

def test_job_config_from_dict_and_overrides():
    c = nb.JobConfig.from_dict({"name": "d", "input_path": "a", "output_path": "b", "tags": ["x"], "dry_run": None})
    assert c.tags == ("x",) and c.dry_run is False
    with pytest.raises(ValueError, match="batchsize"):
        nb.JobConfig.from_dict({"name": "d", "input_path": "a", "output_path": "b", "batchsize": 5})
    c2 = c.with_overrides(batch_size=50)
    assert c2.batch_size == 50 and c.batch_size == 1000
    with pytest.raises(ValueError):
        c.with_overrides(batch_size=-1)


def test_registry_formats():
    assert {"csv", "jsonl", "kv"} <= set(nb.available_formats()) and nb.available_formats() == sorted(nb.available_formats())

def test_parse_formats():
    assert nb.parse("CSV", "a,b\n1,2\n") == [{"a": "1", "b": "2"}]
    assert nb.parse("jsonl", '{"x": 1}\n\n{"x": 2}') == [{"x": 1}, {"x": 2}]
    assert nb.parse("kv", "user=k role=admin\nuser=d") == [{"user": "k", "role": "admin"}, {"user": "d"}]

def test_parse_unknown_and_duplicate():
    with pytest.raises(ValueError, match="available"):
        nb.parse("xml", "<a/>")
    with pytest.raises(ValueError):
        nb.register("csv")(lambda t: [])

def test_register_returns_function():
    @nb.register("upper_test_fmt")
    def f(text):
        return [{"v": text.upper()}]
    assert f("a") == [{"v": "A"}] and nb.parse("upper_test_fmt", "b") == [{"v": "B"}]
