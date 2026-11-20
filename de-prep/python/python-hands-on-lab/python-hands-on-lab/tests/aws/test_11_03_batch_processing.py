"""Tests for 11_python_for_aws/03_batch_processing.ipynb

Run: pytest tests/aws/test_11_03_batch_processing.py -v
"""
import pytest

from labkit.testing import load

nb = load("11_python_for_aws/03_batch_processing.ipynb")


def test_plan_batches():
    assert nb.plan_batches(["aa", "bbb", "c", "dddd", "e"], max_items=2, max_bytes=5) == [["aa", "bbb"], ["c", "dddd"], ["e"]]
    assert nb.plan_batches([], 10, 10) == [] and nb.plan_batches(list("abcdef"), 4, 100) == [list("abcd"), list("ef")]
    with pytest.raises(ValueError):
        nb.plan_batches(["toolong"], 10, 3)


def test_plan_backfill():
    assert nb.plan_backfill("2026-01-30", "2026-02-03", {"2026-01-31"}, 2) == [["2026-01-30", "2026-02-01"], ["2026-02-02", "2026-02-03"]]
    assert nb.plan_backfill("2026-01-01", "2026-01-01", {"2026-01-01"}, 3) == []
    assert len(sum(nb.plan_backfill("2024-02-01", "2024-03-01", set(), 7), [])) == 30
    with pytest.raises(ValueError):
        nb.plan_backfill("2026-02-01", "2026-01-01", set(), 1)


def test_hash_partition():
    recs = [{"id": f"C{i:05d}"} for i in range(10_000)]
    parts = nb.hash_partition(recs, "id", 8)
    assert len(parts) == 8 and sum(map(len, parts)) == 10_000 and nb.skew_ratio(parts) < 1.1
    assert nb.hash_partition(recs, "id", 8) == parts
    import zlib
    assert recs[0] in parts[zlib.crc32(b"C00000") % 8]

def test_skew_ratio():
    assert nb.skew_ratio([[1, 2, 3], [], [4]]) == 2.25 and nb.skew_ratio([]) == 1.0 and nb.skew_ratio([[], []]) == 1.0
    country = nb.hash_partition([{"c": c} for c in ["IN"] * 70 + ["FI"] * 20 + ["SE"] * 10], "c", 8)
    assert nb.skew_ratio(country) > 4


def _part(d, name, rows, header="id,v"):
    (d / name).write_text(header + "\n" + "".join(f"{a},{b}\n" for a, b in rows))

def test_compact_partition(tmp_path):
    for i in range(7):
        _part(tmp_path, f"part-{i:05d}.csv", [(i * 3 + j, "x") for j in range(3)])
    (tmp_path / "_SUCCESS").write_text("")
    r = nb.compact_partition(tmp_path, target_rows=8)
    assert r == {"files_before": 7, "files_after": 3, "rows": 21}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["_SUCCESS", "part-c00000.csv", "part-c00001.csv", "part-c00002.csv"]
    import csv
    ids = [int(row["id"]) for name in ["part-c00000.csv", "part-c00001.csv", "part-c00002.csv"] for row in csv.DictReader(open(tmp_path / name))]
    assert ids == list(range(21))

def test_compact_partition_header_mismatch(tmp_path):
    _part(tmp_path, "part-00000.csv", [(1, "a")]); _part(tmp_path, "part-00001.csv", [(2, "b")], header="id,other")
    with pytest.raises(ValueError):
        nb.compact_partition(tmp_path, 10)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["part-00000.csv", "part-00001.csv"]


def test_process_resumable(tmp_path):
    class WorkerDied(Exception):
        pass
    items = list(range(10))
    calls = []
    def work(batch):
        calls.append(tuple(batch))
        if batch[0] == 6 and not getattr(work, "healed", False):
            raise WorkerDied("worker died")
        return [x * x for x in batch]
    state, out = tmp_path / "state.json", tmp_path / "out"
    with pytest.raises(WorkerDied):
        nb.process_resumable(items, 3, work, state, out)
    assert sorted(p.name for p in out.iterdir()) == ["batch-00000.json", "batch-00001.json"]
    work.healed = True
    r = nb.process_resumable(items, 3, work, state, out)
    assert r == {"ran": [2, 3], "skipped": [0, 1], "total_batches": 4} and (out / "_SUCCESS").exists()
    import json
    assert json.loads((out / "batch-00003.json").read_text()) == [81]
    assert nb.process_resumable(items, 3, work, state, out)["ran"] == []
    with pytest.raises(ValueError):
        nb.process_resumable(items + [10], 3, work, state, out)
    with pytest.raises(ValueError):
        nb.process_resumable(items, 4, work, state, out)
