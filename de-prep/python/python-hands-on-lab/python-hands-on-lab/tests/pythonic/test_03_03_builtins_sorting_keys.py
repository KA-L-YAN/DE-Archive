"""Tests for 03_pythonic_python/03_builtins_sorting_keys.ipynb

Run: pytest tests/pythonic/test_03_03_builtins_sorting_keys.py -v
"""
import pytest

from labkit.testing import load

nb = load("03_pythonic_python/03_builtins_sorting_keys.ipynb")


@pytest.mark.parametrize("steps, expected", [
    ([], "SUCCESS"), ([{"ok": True, "critical": True}], "SUCCESS"),
    ([{"ok": True, "critical": True}, {"ok": False, "critical": False}], "PARTIAL"),
    ([{"ok": False, "critical": False}, {"ok": False, "critical": True}], "FAILED"),
])
def test_pipeline_status(steps, expected):
    assert nb.pipeline_status(steps) == expected


def test_slowest_endpoints():
    recs = [{"path": "/a", "latency_ms": 100}, {"path": "/a", "latency_ms": 300}, {"path": "/b", "latency_ms": 200},
            {"path": "/c", "latency_ms": 50}, {"path": "/d", "latency_ms": 200}, {"latency_ms": 9999}, {"path": "/e"}]
    assert nb.slowest_endpoints(recs) == [("/a", 200.0), ("/b", 200.0), ("/d", 200.0)]
    assert nb.slowest_endpoints(recs, n=10)[-1] == ("/c", 50.0)
    assert nb.slowest_endpoints([]) == []


def test_tenure_extremes():
    emps = [{"emp_id": "E1", "hire_date": "2020-01-01", "status": "active"}, {"emp_id": "E2", "hire_date": "2015-06-01", "status": "terminated"},
            {"emp_id": "E3", "hire_date": "2018-03-03", "status": "on_leave"}, {"emp_id": "E4", "hire_date": "", "status": "active"},
            {"emp_id": "E5", "hire_date": "2024-02-02", "status": "active"}, {"emp_id": "E6", "hire_date": "2024-02-02", "status": "active"}]
    assert nb.tenure_extremes(emps) == ("E3", "E5")
    assert nb.tenure_extremes([]) == (None, None)


def test_rank():
    assert nb.rank({"a": 10, "b": 20, "c": 20, "d": 5}) == [(1, "b", 20), (1, "c", 20), (3, "a", 10), (4, "d", 5)]
    assert nb.rank({}) == [] and nb.rank({"x": 1}) == [(1, "x", 1)]
    assert [r for r, _, _ in nb.rank({"a": 1, "b": 1, "c": 1, "d": 0})] == [1, 1, 1, 4]


def test_natural_sorted_files():
    assert nb.natural_sorted(["part-10.csv", "part-2.csv", "Part-1.csv", "part-1.csv"]) == ["Part-1.csv", "part-1.csv", "part-2.csv", "part-10.csv"]

def test_natural_sorted_versions():
    assert nb.natural_sorted(["v4.10.0", "v4.2.1", "v4.2.10", "v10.0", "v4.2"]) == ["v4.2", "v4.2.1", "v4.2.10", "v4.10.0", "v10.0"]

def test_natural_sorted_mixed():
    assert nb.natural_sorted(["10", "9", "a", "", "a1"]) == ["", "9", "10", "a", "a1"]
