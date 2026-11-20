"""Tests for 05_functions_and_oop/01_args_kwargs.ipynb

Run: pytest tests/functions_oop/test_05_01_args_kwargs.py -v
"""
import pytest

from labkit.testing import load

nb = load("05_functions_and_oop/01_args_kwargs.ipynb")


def test_s3_path():
    assert nb.s3_path("raw", "/sales/", "2026", filename="part-0.csv") == "s3://raw/sales/2026/part-0.csv"
    assert nb.s3_path("raw") == "s3://raw" and nb.s3_path("raw/", "", "/", "a") == "s3://raw/a"
    assert nb.s3_path("b", filename="x.json") == "s3://b/x.json"


def test_format_event():
    assert nb.format_event("job_done", rows=10, job="daily sales") == 'INFO job_done job="daily sales" rows=10'
    assert nb.format_event("x", level="ERROR", event_type="nested") == "ERROR x event_type=nested"
    assert nb.format_event("ping") == "INFO ping"

def test_format_event_signature():
    with pytest.raises(TypeError):
        nb.format_event("x", "ERROR")
    with pytest.raises(TypeError):
        nb.format_event(event_type="x")


def test_merge_records():
    a, b, c = {"id": 1, "city": "Hyd", "phone": None}, {"city": None, "phone": "123"}, {"city": "Vja"}
    assert nb.merge_records(a, b, c) == {"id": 1, "city": "Vja", "phone": "123"}
    assert nb.merge_records(a, b, c, prefer="first") == {"id": 1, "city": "Hyd", "phone": "123"}
    assert nb.merge_records(a, b, skip_none=False) == {"id": 1, "city": None, "phone": "123"}
    assert nb.merge_records() == {} and a == {"id": 1, "city": "Hyd", "phone": None}
    with pytest.raises(ValueError):
        nb.merge_records(a, prefer="middle")


def test_call_with_config_filters():
    def extract(input_path, limit=None):
        return (input_path, limit)
    assert nb.call_with_config(extract, {"input_path": "s3://x", "env": "dev"}) == ("s3://x", None)
    assert nb.call_with_config(extract, {"input_path": "a", "limit": 5}) == ("a", 5)

def test_call_with_config_kwargs_and_kwonly_and_posonly():
    def step(a, /, b, *, c=3, **rest):
        return a, b, c, rest
    assert nb.call_with_config(step, {"a": 1, "b": 2, "z": 9}) == (1, 2, 3, {"z": 9})
    def kw_only(*, x):
        return x
    assert nb.call_with_config(kw_only, {"x": 7, "y": 1}) == 7

def test_call_with_config_missing():
    def load(target, mode, overwrite=False):
        return 1
    with pytest.raises(TypeError, match="target.*mode"):
        nb.call_with_config(load, {"overwrite": True})


def _export(*tables, format: str = "json", limit: int = 0, dry_run: bool = False, title: str = ""):
    return {"tables": tables, "format": format, "limit": limit, "dry_run": dry_run, "title": title}

def _ratio(*, threshold: float = 0.5):
    return threshold

H = {"export": _export, "ratio": _ratio}

def test_dispatch_full():
    r = nb.dispatch('export orders customers --format csv --limit 10 --dry-run --title "Daily Sales"', H)
    assert r == {"tables": ("orders", "customers"), "format": "csv", "limit": 10, "dry_run": True, "title": "Daily Sales"}

def test_dispatch_types_and_defaults():
    assert nb.dispatch("ratio --threshold 0.25", H) == 0.25 and nb.dispatch("ratio", H) == 0.5
    assert nb.dispatch("export", H)["limit"] == 0

def test_dispatch_errors():
    with pytest.raises(ValueError):
        nb.dispatch("import x", H)
    with pytest.raises(TypeError):
        nb.dispatch("export --colour red", H)
    with pytest.raises(TypeError):
        nb.dispatch("export --limit", H)
    with pytest.raises(ValueError):
        nb.dispatch("export --limit ten", H)
