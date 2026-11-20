"""Tests for 08_data_engineering_python/06_idempotent_pipelines.ipynb

Run: pytest tests/etl/test_08_06_idempotent_pipelines.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/06_idempotent_pipelines.ipynb")


def test_run_id():
    a = nb.run_id("daily_sales", {"date": "2026-01-05", "countries": ["IN", "FI"]})
    b = nb.run_id("daily_sales", {"countries": ["IN", "FI"], "date": "2026-01-05"})
    assert a == b and a.startswith("daily_sales-") and len(a) == len("daily_sales-") + 12
    assert a != nb.run_id("daily_sales", {"date": "2026-01-06", "countries": ["IN", "FI"]})
    from datetime import date
    assert nb.run_id("j", {"d": date(2026, 1, 5)}) == nb.run_id("j", {"d": "2026-01-05"})


def test_write_partition(tmp_path):
    p = nb.write_partition(tmp_path, {"dt": "2026-01-05", "country": "IN"}, [{"b": 2, "a": 1}])
    assert p == tmp_path / "dt=2026-01-05" / "country=IN" and (p / "part-00000.jsonl").read_text() == '{"a": 1, "b": 2}\n'
    (p / "stale-file.jsonl").write_text("old")
    first = (p / "part-00000.jsonl").read_bytes()
    nb.write_partition(tmp_path, {"dt": "2026-01-05", "country": "IN"}, [{"a": 1, "b": 2}])
    assert sorted(x.name for x in p.iterdir()) == ["part-00000.jsonl"] and (p / "part-00000.jsonl").read_bytes() == first
    assert not [x for x in (tmp_path / "dt=2026-01-05").iterdir() if x.name.startswith(".tmp")]


def test_append_unique(tmp_path):
    p = tmp_path / "x" / "events.jsonl"
    batch = [{"id": 1}, {"id": 2}, {"id": 1}]
    assert nb.append_unique(p, batch, "id") == 2 and nb.append_unique(p, batch, "id") == 0
    assert nb.append_unique(p, [{"id": 3}], "id") == 1 and len(p.read_text().splitlines()) == 3


from datetime import datetime as _dt, timedelta as _td, timezone as _tz

class Clock:
    def __init__(self): self.now = _dt(2026, 1, 5, 10, 0, tzinfo=_tz.utc)
    def __call__(self): return self.now

def test_run_ledger_lifecycle(tmp_path):
    clock = Clock()
    led = nb.RunLedger(tmp_path / "ledger.json", stale_after_seconds=600, clock=clock)
    assert led.should_run("sales", "2026-01-05", "h1")
    led.start("sales", "2026-01-05", "h1")
    assert not led.should_run("sales", "2026-01-05", "h1")
    clock.now += _td(minutes=11)
    assert led.should_run("sales", "2026-01-05", "h1")
    led.start("sales", "2026-01-05", "h1"); led.succeed("sales", "2026-01-05", {"rows": 10})
    led2 = nb.RunLedger(tmp_path / "ledger.json", clock=clock)
    assert not led2.should_run("sales", "2026-01-05", "h1") and led2.should_run("sales", "2026-01-05", "h2") and led2.should_run("sales", "2026-01-05", "h1", force=True)
    entry = led2.history()["sales|2026-01-05"]
    assert entry["status"] == "success" and entry["attempts"] == 2 and entry["stats"] == {"rows": 10}

def test_run_ledger_failure(tmp_path):
    led = nb.RunLedger(tmp_path / "l.json", clock=Clock())
    led.start("j", "p", "h"); led.fail("j", "p", ValueError("bad input"))
    assert led.should_run("j", "p", "h") and led.history()["j|p"]["error"] == "bad input"


def test_run_daily_job(tmp_path):
    import shutil
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "datasets/daily"
    daily = tmp_path / "daily"
    shutil.copytree(src, daily)
    out, ledger = tmp_path / "out", tmp_path / "state" / "ledger.json"
    r1 = nb.run_daily_job(daily, out, ledger)
    assert len(r1["processed"]) == 7 and r1["skipped"] == [] and r1["failed"] == []
    assert r1["stats"]["2026-01-07"] == {"read": 0, "loaded": 0, "rejected": 0, "duplicates": 0}
    assert r1["stats"]["2026-01-05"]["rejected"] > r1["stats"]["2026-01-04"]["rejected"]
    assert all(s["read"] == s["loaded"] + s["rejected"] + s["duplicates"] for s in r1["stats"].values())
    r2 = nb.run_daily_job(daily, out, ledger)
    assert r2["processed"] == [] and len(r2["skipped"]) == 7
    f = daily / "dt=2026-01-03" / "orders_20260103_part1.csv"
    f.write_text(f.read_text() + "O9999999,C00001,P0001,1,10.0,2026-01-03T10:00:00Z,PLACED,2026-01-03T10:00:00Z,web,IN\n")
    r3 = nb.run_daily_job(daily, out, ledger)
    assert r3["processed"] == ["2026-01-03"] and len(r3["skipped"]) == 6
    lines = (out / "orders" / "dt=2026-01-03" / "part-00000.jsonl").read_text().splitlines()
    assert any('"O9999999"' in l for l in lines)
    assert nb.run_daily_job(daily, out, ledger, force=True)["processed"] == r1["processed"]
