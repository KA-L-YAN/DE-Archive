"""Tests for 06_files_json_csv/03_json_config_env.ipynb

Run: pytest tests/files/test_06_03_json_config_env.py -v
"""
import pytest

from labkit.testing import load

nb = load("06_files_json_csv/03_json_config_env.ipynb")


def test_jsonl_roundtrip(tmp_path):
    from datetime import date
    from decimal import Decimal
    p = tmp_path / "x" / "a.jsonl"
    assert nb.write_jsonl(p, iter([{"city": "Hyderabad ₹"}, {"d": date(2026, 1, 5), "amt": Decimal("1.50")}])) == 2
    assert nb.read_jsonl(p) == [{"city": "Hyderabad ₹"}, {"d": "2026-01-05", "amt": "1.50"}]
    assert "₹" in p.read_text(encoding="utf-8")


def test_load_config(tmp_path):
    import json
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"batch_size": 500, "ratio": 0.2, "dry_run": False, "dedupe_key": ["order_id"], "log_level": "INFO"}))
    env = {"LAB_BATCH_SIZE": "250", "LAB_RATIO": "0.5", "LAB_DRY_RUN": "Yes", "LAB_DEDUPE_KEY": "order_id, line_no ,", "LAB_UNKNOWN": "x"}
    assert nb.load_config(p, env) == {"batch_size": 250, "ratio": 0.5, "dry_run": True, "dedupe_key": ["order_id", "line_no"], "log_level": "INFO"}
    assert nb.load_config(p, {})["batch_size"] == 500
    with pytest.raises(ValueError):
        nb.load_config(p, {"LAB_DRY_RUN": "maybe"})

def test_load_config_real_file():
    from pathlib import Path
    cfg = nb.load_config(Path(__file__).resolve().parents[2] / "datasets/config/pipeline.json", {"LAB_LOG_LEVEL": "DEBUG"})
    assert cfg["log_level"] == "DEBUG" and cfg["batch_size"] == 500


def test_summarize_customers(tmp_path):
    import json
    src = tmp_path / "c.json"
    src.write_text(json.dumps([{"country": "IN", "segment": "smb", "is_active": True, "signup_date": "2024-01-02"},
                               {"country": "FI", "segment": "smb", "is_active": "false", "signup_date": "2023-05-05"},
                               {"country": "IN", "segment": "retail", "is_active": "true"}]))
    s = nb.summarize_customers(src, tmp_path / "out" / "s.json")
    assert s == {"total": 3, "active": 2, "by_country": {"FI": 1, "IN": 2}, "by_segment": {"retail": 1, "smb": 2}, "signup_range": ["2023-05-05", "2024-01-02"]}
    assert json.loads((tmp_path / "out" / "s.json").read_text()) == s
    src.write_text("[]")
    assert nb.summarize_customers(src, tmp_path / "e.json")["signup_range"] == [None, None]


SCHEMA = {"id": int, "customer": {"name": str, "email?": str}, "items": [{"name": str, "price": (int, float)}]}

def test_validate_json_ok():
    assert nb.validate_json({"id": 1, "customer": {"name": "P", "email": None}, "items": []}, SCHEMA) == []

def test_validate_json_errors():
    doc = {"id": True, "customer": {"email": 5}, "items": [{"name": "L", "price": 1.5}, {"name": 2, "price": "x"}]}
    assert nb.validate_json(doc, SCHEMA) == ["$.id: expected int, got bool", "$.customer.name: missing", "$.customer.email: expected str, got int",
                                             "$.items[1].name: expected str, got int", "$.items[1].price: expected int|float, got str"]
    assert nb.validate_json({"id": 1, "customer": [], "items": {}}, SCHEMA) == ["$.customer: expected object, got list", "$.items: expected list, got dict"]


DEFAULTS = {"env": "local", "batch_size": 1000, "dry_run": False, "ratio": 0.1, "tags": [], "log_level": "INFO"}

def test_settings_layers(tmp_path):
    import json
    j = tmp_path / "c.json"; j.write_text(json.dumps({"batch_size": 500, "input_dir": "data/in"}))
    e = tmp_path / ".env"
    e.write_text("# comment\n\nexport LAB_ENV=dev\nLAB_RATIO='0.5'\nLOG_LEVEL=DEBUG # inline\nLAB_TAGS=\"a, b\"\nbad line\n")
    s = nb.Settings(DEFAULTS, json_path=j, env_file=e, environ={"LAB_BATCH_SIZE": "250", "PATH": "/usr/bin", "LAB_DRY_RUN": "on"},
                    overrides={"env": "prod"}, required=["input_dir"])
    assert s.as_dict() == {"env": "prod", "batch_size": 250, "dry_run": True, "ratio": 0.5, "tags": ["a", "b"], "log_level": "DEBUG", "input_dir": "data/in"}
    assert [s.source_of(k) for k in ["env", "batch_size", "ratio", "input_dir", "dry_run"]] == ["overrides", "environ", "env_file", "json", "environ"]
    assert s["ratio"] == 0.5 and s.get("nope", 1) == 1 and "path" not in s and "tags" in s

def test_settings_required_and_missing_files(tmp_path):
    with pytest.raises(ValueError, match="input_dir.*output_dir"):
        nb.Settings(DEFAULTS, environ={}, required=["input_dir", "output_dir"])
    s = nb.Settings(DEFAULTS, env_file=tmp_path / "nope.env", environ={})
    assert s.source_of("env") == "defaults"

def test_parse_env_file():
    assert nb.parse_env_file("A=1\nB = ' x # y '\nC=v # c\n#D=4") == {"A": "1", "B": " x # y ", "C": "v"}
