"""Tests for Project 4 — Incremental Data Pipeline.  Run: pytest tests/projects/test_project_04_incremental_etl.py -v"""
import json
import shutil
from pathlib import Path

import pytest

from labkit.testing import import_project

PROJECT = "project_04_incremental_etl"
state_mod = import_project(PROJECT, "incremental_etl.state")
processing = import_project(PROJECT, "incremental_etl.processing")
warehouse_mod = import_project(PROJECT, "incremental_etl.warehouse")
pipeline = import_project(PROJECT, "incremental_etl.pipeline")
cli = import_project(PROJECT, "incremental_etl.cli")

DAILY = Path(__file__).resolve().parents[2] / "datasets/daily"
HEADER = "order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"


def line(oid, upd="2026-01-01T10:00:00Z", status="PLACED", qty=1, ts="2026-01-01T09:00:00Z"):
    return f"{oid},C1,P1,{qty},10.0,{ts},{status},{upd},web,IN\n"


def arrive(src_days, inbox):
    for day in src_days:
        shutil.copytree(DAILY / f"dt={day}", inbox / f"dt={day}")


# ---------------------------------------------------------------- units
def test_state_roundtrip_and_corruption(tmp_path):
    s = state_mod.PipelineState(tmp_path / "s.json")
    s.record_file("dt=1/a.csv", "abc", 10, "r1"); s.order_index["O1"] = "2026-01-01T00:00:00Z"; s.record_run({"run_id": "r1"}); s.save()
    s2 = state_mod.PipelineState(tmp_path / "s.json")
    assert s2.is_processed("dt=1/a.csv", "abc") and not s2.is_processed("dt=1/a.csv", "zzz") and s2.processed_hashes() == {"abc": "dt=1/a.csv"}
    assert s2.order_index == {"O1": "2026-01-01T00:00:00Z"} and s2.runs == [{"run_id": "r1"}]
    (tmp_path / "bad.json").write_text("{nope")
    with pytest.raises(state_mod.StateError):
        state_mod.PipelineState(tmp_path / "bad.json")
    (tmp_path / "v2.json").write_text(json.dumps({"version": 99}))
    with pytest.raises(state_mod.StateError):
        state_mod.PipelineState(tmp_path / "v2.json")


def test_discover_and_classify(tmp_path):
    (tmp_path / "dt=2026-01-02").mkdir(); (tmp_path / "dt=2026-01-01").mkdir()
    (tmp_path / "dt=2026-01-01" / "a.csv").write_text("x"); (tmp_path / "dt=2026-01-02" / "b.csv").write_text("y")
    (tmp_path / "dt=2026-01-02" / "copy_of_a.csv").write_text("x"); (tmp_path / "dt=2026-01-02" / ".tmp.csv").write_text("z")
    files = processing.discover(tmp_path)
    assert [f.key for f in files] == ["dt=2026-01-01/a.csv", "dt=2026-01-02/b.csv", "dt=2026-01-02/copy_of_a.csv"] and files[0].partition == "2026-01-01"
    groups = processing.classify(files, {}, {})
    assert [f.key for f in groups["new"]] == ["dt=2026-01-01/a.csv", "dt=2026-01-02/b.csv"] and [f.key for f in groups["redelivered"]] == ["dt=2026-01-02/copy_of_a.csv"]
    processed = {"dt=2026-01-01/a.csv": {"sha256": files[0].sha256}, "dt=2026-01-02/b.csv": {"sha256": "old"}}
    g2 = processing.classify(files[:2], processed, {files[0].sha256: "dt=2026-01-01/a.csv"})
    assert [f.key for f in g2["unchanged"]] == ["dt=2026-01-01/a.csv"] and [f.key for f in g2["changed"]] == ["dt=2026-01-02/b.csv"]


def test_validate_and_select_changes():
    rec = processing.validate({"order_id": "O1", "customer_id": "C1", "product_id": "P1", "quantity": "2", "unit_price": "1.25", "order_ts": "2026-01-01T09:00:00Z",
                               "status": "shipped", "updated_at": "2026-01-01T10:00:00Z", "channel": "WEB", "country": "in"})
    assert (rec["amount"], rec["status"], rec["order_date"], rec["channel"]) == (2.5, "SHIPPED", "2026-01-01", "web")
    for bad in ({**rec, "quantity": "0"}, {**rec, "status": "lost"}, {**rec, "order_ts": "yesterday"}, {**rec, "customer_id": ""}):
        with pytest.raises(ValueError):
            processing.validate({k: str(v) for k, v in bad.items()})
    a = {"order_id": "O1", "updated_at": "2026-01-01T10:00:00Z"}
    b = {"order_id": "O1", "updated_at": "2026-01-02T10:00:00Z"}
    c = {"order_id": "O2", "updated_at": "2026-01-01T00:00:00Z"}
    assert processing.select_changes([a, b, c], {"O2": "2026-01-05T00:00:00Z"}) == ([b], 2)
    assert processing.select_changes([b, a], {}) == ([b], 1)


def test_warehouse_upsert_and_quarantine(tmp_path):
    wh = warehouse_mod.Warehouse(tmp_path / "wh")
    assert wh.upsert([{"order_id": "B", "order_date": "2026-01-01", "v": 1}, {"order_id": "A", "order_date": "2026-01-01", "v": 1},
                      {"order_id": "C", "order_date": "2026-01-02", "v": 1}]) == {"2026-01-01": 2, "2026-01-02": 1}
    wh.upsert([{"order_id": "A", "order_date": "2026-01-01", "v": 2, "_line": 9}])
    part = wh.load_partition("2026-01-01")
    assert part == {"A": {"order_id": "A", "order_date": "2026-01-01", "v": 2}, "B": {"order_id": "B", "order_date": "2026-01-01", "v": 1}}
    lines = (tmp_path / "wh/orders/order_date=2026-01-01/part-00000.jsonl").read_text().splitlines()
    assert [json.loads(l)["order_id"] for l in lines] == ["A", "B"] and len(wh.all_orders()) == 3
    assert wh.quarantine([], "r1", "dt=x/a.csv") is None
    q = wh.quarantine([{"x": 1}], "r1", "dt=x/a.csv")
    assert q.name == "dt=x__a.csv.jsonl" and q.read_text() == '{"x": 1}\n'


# ---------------------------------------------------------------- end to end
def test_incremental_days_and_idempotency(tmp_path):
    inbox, wh, st = tmp_path / "inbox", tmp_path / "wh", tmp_path / "state.json"
    inbox.mkdir()
    totals = []
    for day in ["2026-01-01", "2026-01-02", "2026-01-03"]:
        arrive([day], inbox)
        s = pipeline.run(inbox, wh, st, run_id=f"run-{day}")
        assert s["files_processed"] == 2 and s["files_unchanged"] == 2 * len(totals)
        totals.append(s)
    assert totals[2]["rows_stale"] >= 15                    # late duplicates from day 2 are ignored
    again = pipeline.run(inbox, wh, st)
    assert again["files_processed"] == 0 and again["rows_upserted"] == 0 and again["files_unchanged"] == 6
    arrive(["2026-01-04", "2026-01-05", "2026-01-06", "2026-01-07"], inbox)
    s = pipeline.run(inbox, wh, st)
    assert s["files_redelivered"] == 1 and s["files_processed"] == 7
    orders = warehouse_mod.Warehouse(wh).all_orders()
    full = pipeline.run(inbox, tmp_path / "wh2", tmp_path / "state2.json")
    assert orders == warehouse_mod.Warehouse(tmp_path / "wh2").all_orders() and full["orders_in_warehouse"] == len(orders)
    assert list((wh / "quarantine").glob("*/*.jsonl"))


def test_changed_file_applies_only_newer_versions(tmp_path):
    inbox = tmp_path / "in" / "dt=2026-01-01"
    inbox.mkdir(parents=True)
    f = inbox / "orders.csv"
    f.write_text(HEADER + line("O1") + line("O2"))
    pipeline.run(tmp_path / "in", tmp_path / "wh", tmp_path / "s.json")
    f.write_text(HEADER + line("O1", upd="2026-01-01T11:00:00Z", status="SHIPPED") + line("O2") + line("O3"))
    s = pipeline.run(tmp_path / "in", tmp_path / "wh", tmp_path / "s.json")
    assert s["files_changed"] == 1 and s["rows_upserted"] == 2 and s["rows_stale"] == 1
    orders = warehouse_mod.Warehouse(tmp_path / "wh").all_orders()
    assert orders["O1"]["status"] == "SHIPPED" and set(orders) == {"O1", "O2", "O3"}


def test_crash_recovery(tmp_path):
    inbox = tmp_path / "inbox"
    shutil.copytree(DAILY, inbox)
    with pytest.raises(pipeline.SimulatedCrash):
        pipeline.run(inbox, tmp_path / "wh", tmp_path / "s.json", crash_after_files=5)
    assert len(state_mod.PipelineState(tmp_path / "s.json").files) == 5 + 1        # 5 processed + the redelivered marker
    resumed = pipeline.run(inbox, tmp_path / "wh", tmp_path / "s.json")
    assert resumed["files_processed"] == 8
    clean = pipeline.run(inbox, tmp_path / "wh_clean", tmp_path / "s_clean.json")
    assert warehouse_mod.Warehouse(tmp_path / "wh").all_orders() == warehouse_mod.Warehouse(tmp_path / "wh_clean").all_orders()
    assert clean["files_processed"] == 13


def test_full_refresh_and_cli(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    shutil.copytree(DAILY, inbox)
    args = ["--log-level", "ERROR", "run", "--input", str(inbox), "--warehouse", str(tmp_path / "wh"), "--state", str(tmp_path / "s.json")]
    assert cli.main(args) == 0 and cli.main(args + ["--full-refresh"]) == 0
    out = capsys.readouterr().out
    assert '"files_processed": 13' in out.split("}\n{")[-1]
    assert cli.main(["status", "--state", str(tmp_path / "s.json")]) == 0
    (tmp_path / "bad.json").write_text("{")
    assert cli.main(["status", "--state", str(tmp_path / "bad.json")]) == 2
    assert cli.main(["run", "--input", str(tmp_path / "missing"), "--warehouse", "w", "--state", "s"]) == 2
