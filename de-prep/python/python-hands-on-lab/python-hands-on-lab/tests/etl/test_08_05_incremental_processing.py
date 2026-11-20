"""Tests for 08_data_engineering_python/05_incremental_processing.ipynb

Run: pytest tests/etl/test_08_05_incremental_processing.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/05_incremental_processing.ipynb")


def test_files_to_process():
    avail = ["dt=2026-01-02/b.csv", "dt=2026-01-01/a.csv", "dt=2026-01-02/a.csv", "dt=2026-01-01/a.csv"]
    assert nb.files_to_process(avail, {"dt=2026-01-01/a.csv"}) == ["dt=2026-01-02/a.csv", "dt=2026-01-02/b.csv"]
    assert nb.files_to_process([], set()) == []


def test_checkpoint_roundtrip(tmp_path):
    cp = nb.Checkpoint(tmp_path / "state" / "cp.json")
    assert cp.processed == {} and cp.watermark is None and not cp.is_processed("a")
    cp.mark("a", "sha1"); cp.advance("2026-01-02"); cp.advance("2026-01-01"); cp.save()
    cp2 = nb.Checkpoint(tmp_path / "state" / "cp.json")
    assert cp2.is_processed("a") and cp2.is_processed("a", "sha1") and not cp2.is_processed("a", "other") and cp2.watermark == "2026-01-02"
    assert [p.name for p in (tmp_path / "state").iterdir()] == ["cp.json"]

def test_checkpoint_corrupt(tmp_path):
    p = tmp_path / "cp.json"; p.write_text("{oops")
    with pytest.raises(ValueError):
        nb.Checkpoint(p)


RECS = [{"id": i, "ts": f"2026-01-01T00:0{i}:00Z"} for i in range(6)]

def test_select_new():
    sel, wm = nb.select_new(RECS, "2026-01-01T00:03:00Z", "ts")
    assert [r["id"] for r in sel] == [4, 5] and wm == "2026-01-01T00:05:00Z"
    sel, wm = nb.select_new(RECS, "2026-01-01T00:03:00Z", "ts", lookback_seconds=120)
    assert [r["id"] for r in sel] == [2, 3, 4, 5]
    assert nb.select_new(RECS, None, "ts")[0] == RECS and nb.select_new([], "2026-01-01T00:00:00Z", "ts") == ([], "2026-01-01T00:00:00Z")
    assert nb.select_new([], None, "ts") == ([], None)


def test_upsert():
    target = {"O1": {"id": "O1", "v": 1, "s": "PLACED"}}
    changes = [{"id": "O1", "v": 3, "s": "SHIPPED"}, {"id": "O1", "v": 2, "s": "PACKED"}, {"id": "O2", "v": 1, "s": "PLACED"}, {"id": "O2", "v": 1, "s": "PLACED"}]
    assert nb.upsert(target, changes, "id", "v") == {"inserted": 1, "updated": 1, "deleted": 0, "skipped_stale": 2}
    assert target == {"O1": {"id": "O1", "v": 3, "s": "SHIPPED"}, "O2": {"id": "O2", "v": 1, "s": "PLACED"}}

def test_upsert_order_independent_with_deletes():
    import itertools
    changes = [{"id": "A", "v": 1, "s": "x"}, {"id": "A", "v": 3, "_op": "delete"}, {"id": "A", "v": 2, "s": "y"}, {"id": "B", "v": 5, "s": "z"}]
    finals = set()
    for perm in itertools.permutations(changes):
        t = {}
        nb.upsert(t, list(perm), "id", "v")
        finals.add(tuple(sorted((k, tuple(sorted(v.items()))) for k, v in t.items())))
    assert finals == {(("B", (("id", "B"), ("s", "z"), ("v", 5))),)}


def test_update_daily_aggregates():
    s0 = {"watermark": None, "days": {}}
    s1, changed, dropped = nb.update_daily_aggregates(s0, [{"event_id": "e1", "date": "2026-01-05", "amount": 10.0}, {"event_id": "e2", "date": "2026-01-04", "amount": 5.5}])
    assert s0 == {"watermark": None, "days": {}} and changed == ["2026-01-04", "2026-01-05"] and dropped == 0 and s1["watermark"] == "2026-01-05"
    batch = [{"event_id": "e1", "date": "2026-01-05", "amount": 10.0}, {"event_id": "e3", "date": "2026-01-03", "amount": 1.0},
             {"event_id": "e4", "date": "2026-01-02", "amount": 99.0}, {"event_id": "e5", "date": "2026-01-07", "amount": 2.25}]
    s2, changed, dropped = nb.update_daily_aggregates(s1, batch, allowed_lateness_days=2)
    assert changed == ["2026-01-03", "2026-01-07"] and dropped == 1 and s2["watermark"] == "2026-01-07"
    assert s2["days"]["2026-01-05"]["revenue"] == 10.0 and s2["days"]["2026-01-05"]["events"] == 1 and "2026-01-02" not in s2["days"]
    s3, changed, dropped = nb.update_daily_aggregates(s2, [{"event_id": "late", "date": "2026-01-04", "amount": 1}])
    assert dropped == 1 and changed == [] and s3["watermark"] == "2026-01-07"
