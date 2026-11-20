"""Tests for Project 2 — CSV ETL Pipeline.  Run: pytest tests/projects/test_project_02_csv_etl.py -v"""
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from labkit.testing import import_project

PROJECT = "project_02_csv_etl"
config_mod = import_project(PROJECT, "csv_etl.config")
io_mod = import_project(PROJECT, "csv_etl.io")
rules = import_project(PROJECT, "csv_etl.rules")
pipeline = import_project(PROJECT, "csv_etl.pipeline")
cli = import_project(PROJECT, "csv_etl.cli")

ROOT = Path(__file__).resolve().parents[2]
HEADER = "order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"
RAW = {"order_id": "O1", "customer_id": "C1", "product_id": "P1", "quantity": "2", "unit_price": "10.5", "order_ts": "2026-02-01T10:00:00Z",
       "status": "shipped", "updated_at": "2026-02-01T12:00:00Z", "channel": "WEB", "country": "in", "_source": "a.csv", "_line": 2}


def row(oid="O1", qty="1", price="10", ts="2026-02-01T10:00:00Z", upd="2026-02-01T10:00:00Z", status="PLACED", cust="C1", country="IN"):
    return f"{oid},{cust},P1,{qty},{price},{ts},{status},{upd},web,{country}\n"


@pytest.fixture
def incoming(tmp_path):
    d = tmp_path / "incoming"
    d.mkdir()
    (d / "orders_01.csv").write_text(HEADER + row("O1") + row("O2", qty="0") + row("O3", price="N/A") + row("O4", status="lost"))
    (d / "orders_02.csv").write_text(HEADER + row("O1", upd="2026-02-02T10:00:00Z", status="DELIVERED") + row("O5", cust="C9") + "O6,C1\n")
    (d / "orders_03.csv.tmp").write_text(HEADER + row("O99"))
    (d / "_SUCCESS").write_text("")
    (d / "customers.json").write_text(json.dumps([{"customer_id": "C1", "segment": "smb"}]))
    return d


# ---------------------------------------------------------------- config
def test_load_config(tmp_path, incoming):
    cfg = config_mod.load_config(None, input_dir=incoming, output_dir=tmp_path / "out")
    assert cfg.pattern == "orders_*.csv" and isinstance(cfg.input_dir, Path) and cfg.max_reject_ratio == 0.25
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"input_dir": str(incoming), "output_dir": str(tmp_path / "o"), "max_reject_ratio": 0.5, "allowed_status": ["PLACED"]}))
    cfg2 = config_mod.load_config(f, max_reject_ratio=0.1, pattern=None)
    assert cfg2.max_reject_ratio == 0.1 and cfg2.allowed_status == ("PLACED",)


@pytest.mark.parametrize("kw", [dict(max_reject_ratio=2), dict(key="nope"), dict(input_dir="does/not/exist"), dict(unknown_key=1)])
def test_load_config_errors(tmp_path, incoming, kw):
    base = dict(input_dir=incoming, output_dir=tmp_path / "out")
    with pytest.raises(config_mod.ConfigError):
        config_mod.load_config(None, **{**base, **kw})


# ---------------------------------------------------------------- io
def test_discover_and_read(incoming):
    files = io_mod.discover_files(incoming, "orders_*.csv")
    assert [f.name for f in files] == ["orders_01.csv", "orders_02.csv"]
    rows = list(io_mod.read_rows(files[1]))
    assert rows[0]["order_id"] == "O1" and rows[0]["_line"] == 2 and rows[2]["_error"].startswith("expected 10 fields") and rows[2]["_raw"] == ["O6", "C1"]


def test_read_rows_bom_and_headers(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(" Order ID ,Unit-Price\nO1,5\n\n", encoding="utf-8-sig")
    assert list(io_mod.read_rows(p)) == [{"order_id": "O1", "unit_price": "5", "_source": "x.csv", "_line": 2}]


def test_write_csv_atomic(tmp_path):
    info = io_mod.write_csv_atomic(tmp_path / "d" / "o.csv", iter([{"a": 1, "b": 2, "z": 9}]), ["a", "b"])
    assert info["rows"] == 1 and (tmp_path / "d" / "o.csv").read_text().splitlines() == ["a,b", "1,2"]
    assert info["sha256"] == io_mod.sha256_file(tmp_path / "d" / "o.csv") and len(list((tmp_path / "d").iterdir())) == 1


# ---------------------------------------------------------------- rules
def test_validate_row_ok():
    r = rules.validate_row(RAW, config_mod.DEFAULT_COLUMNS, ["SHIPPED"])
    assert (r["quantity"], r["unit_price"], r["status"], r["channel"], r["country"]) == (2, 10.5, "SHIPPED", "web", "IN")
    assert r["order_ts"] == datetime(2026, 2, 1, 10, tzinfo=timezone.utc) and r["_line"] == 2


@pytest.mark.parametrize("field, value", [("quantity", "0"), ("quantity", "x"), ("unit_price", "-1"), ("unit_price", ""), ("status", "LOST"),
                                          ("order_ts", "yesterday"), ("updated_at", "2026-01-01T00:00:00Z"), ("country", "IND"), ("customer_id", " ")])
def test_validate_row_errors(field, value):
    with pytest.raises(rules.ValidationError) as info:
        rules.validate_row({**RAW, field: value}, config_mod.DEFAULT_COLUMNS, ["SHIPPED"])
    assert info.value.field == field and isinstance(info.value, ValueError)


def test_transform_dedupe_aggregate():
    base = rules.validate_row(RAW, config_mod.DEFAULT_COLUMNS, ["SHIPPED", "CANCELLED"])
    t = rules.transform(base, {"C1": {"segment": "smb"}})
    assert t["amount"] == 21.0 and t["order_date"] == "2026-02-01" and t["customer_segment"] == "smb" and t["is_known_customer"]
    other = rules.transform({**base, "order_id": "O2", "customer_id": "C2", "status": "CANCELLED"}, {})
    newer = {**t, "updated_at": datetime(2026, 2, 3, tzinfo=timezone.utc), "quantity": 3, "amount": 31.5}
    deduped, removed = rules.dedupe_latest([t, other, newer], "order_id", "updated_at")
    assert removed == 1 and [r["order_id"] for r in deduped] == ["O1", "O2"] and deduped[0]["quantity"] == 3
    assert rules.daily_summary(deduped) == [{"order_date": "2026-02-01", "country": "IN", "channel": "web", "orders": 1, "units": 3, "revenue": 31.5}]
    assert rules.customer_summary(deduped) == [{"customer_id": "C1", "segment": "smb", "orders": 1, "revenue": 31.5, "first_order": "2026-02-01", "last_order": "2026-02-01"}]


# ---------------------------------------------------------------- pipeline
def test_pipeline_run(tmp_path, incoming):
    cfg = config_mod.load_config(None, input_dir=incoming, output_dir=tmp_path / "out", max_reject_ratio=0.6)
    audit = pipeline.run(cfg, run_id="test-run")
    t = audit["totals"]
    assert (t["files"], t["rows_read"], t["valid"], t["rejected"], t["duplicates_removed"], t["unique_orders"]) == (2, 7, 3, 4, 1, 2)
    assert audit["status"] == "SUCCEEDED" and t["unknown_customers"] == 1 and t["reject_ratio"] == round(4 / 7, 4)
    clean = list(csv.DictReader(open(tmp_path / "out" / "clean_orders.csv")))
    assert [(c["order_id"], c["status"]) for c in clean] == [("O1", "DELIVERED"), ("O5", "PLACED")]
    rejected = list(csv.DictReader(open(tmp_path / "out" / "rejected_rows.csv")))
    assert {r["_error_field"] for r in rejected} == {"quantity", "unit_price", "status", "_row"}
    saved = json.loads((tmp_path / "out" / "audit.json").read_text())
    assert saved == audit and {o["name"] for o in audit["outputs"]} == {"rejected_rows.csv", "clean_orders.csv", "daily_summary.csv", "customer_summary.csv"}


def test_pipeline_reject_threshold(tmp_path, incoming):
    cfg = config_mod.load_config(None, input_dir=incoming, output_dir=tmp_path / "out", max_reject_ratio=0.1)
    with pytest.raises(pipeline.RejectThresholdExceeded) as info:
        pipeline.run(cfg)
    assert info.value.audit["status"] == "FAILED" and (tmp_path / "out" / "audit.json").exists()
    assert not (tmp_path / "out" / "clean_orders.csv").exists() and (tmp_path / "out" / "rejected_rows.csv").exists()


def test_pipeline_idempotent_outputs(tmp_path, incoming):
    cfg = config_mod.load_config(None, input_dir=incoming, output_dir=tmp_path / "out", max_reject_ratio=0.9)
    a = {o["name"]: o["sha256"] for o in pipeline.run(cfg)["outputs"]}
    b = {o["name"]: o["sha256"] for o in pipeline.run(cfg)["outputs"]}
    assert a == b


def test_cli_real_incoming(tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["--input", str(ROOT / "datasets/incoming"), "--output", str(out)]) == 0
    audit = json.loads((out / "audit.json").read_text())
    assert audit["totals"]["files"] == 3 and audit["totals"]["duplicates_removed"] > 20 and audit["totals"]["rejected"] > 5
    assert cli.main(["--input", str(ROOT / "datasets/incoming"), "--output", str(out), "--pattern", "*.csv", "--max-reject-ratio", "0.001"]) == 1
    assert cli.main(["--input", str(tmp_path / "nope"), "--output", str(out)]) == 2
