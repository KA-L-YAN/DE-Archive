"""Tests for 06_files_json_csv/01_pathlib_and_files.ipynb

Run: pytest tests/files/test_06_01_pathlib_and_files.py -v
"""
import pytest

from labkit.testing import load

nb = load("06_files_json_csv/01_pathlib_and_files.ipynb")


def test_discover_files(tmp_path):
    for name in ["b.csv", "a.csv", ".hidden.csv", "_SUCCESS", "c.csv.tmp", "d.json", "e.part"]:
        (tmp_path / name).write_text("x")
    (tmp_path / "dir.csv").mkdir()
    assert [p.name for p in nb.discover_files(tmp_path)] == ["a.csv", "b.csv"]
    assert [p.name for p in nb.discover_files(tmp_path, "*")] == ["a.csv", "b.csv", "d.json"]

def test_discover_files_real():
    from pathlib import Path
    found = nb.discover_files(Path(__file__).resolve().parents[2] / "datasets/incoming")
    assert [p.name for p in found] == ["corrupt.csv", "orders_01.csv", "orders_02.csv", "orders_03.csv"]


def test_partition_path():
    from pathlib import Path
    assert nb.partition_path("out", year=2026, month="01") == Path("out/year=2026/month=01")
    assert nb.partition_path("out") == Path("out")

def test_parse_partitions():
    assert nb.parse_partitions("out/sales/dt=2026-01-05/region=IN/part-0.csv") == {"dt": "2026-01-05", "region": "IN"}
    assert nb.parse_partitions("x/q=a=b/f") == {"q": "a=b"} and nb.parse_partitions("plain/file.csv") == {}


def test_inventory(tmp_path):
    (tmp_path / "dt=2026-01-01").mkdir(); (tmp_path / "dt=2026-01-01" / "a.csv").write_text("12345")
    (tmp_path / "b.json").write_text("{}")
    files, total = nb.inventory(tmp_path)
    assert total == 7 and [f["path"] for f in files] == ["b.json", "dt=2026-01-01/a.csv"]
    assert files[1]["partitions"] == {"dt": "2026-01-01"} and files[1]["suffix"] == ".csv" and files[0]["partitions"] == {}

def test_inventory_real_daily():
    from pathlib import Path
    files, total = nb.inventory(Path(__file__).resolve().parents[2] / "datasets/daily")
    assert len(files) == 14 and total > 10_000 and {f["partitions"]["dt"] for f in files} >= {"2026-01-01", "2026-01-07"}


def test_archive_files(tmp_path):
    inbox, arch = tmp_path / "in", tmp_path / "archive"
    inbox.mkdir()
    for n in ["orders.csv", "x.csv"]:
        (inbox / n).write_text(n)
    (arch / "r1").mkdir(parents=True); (arch / "r1" / "orders.csv").write_text("old")
    moved = nb.archive_files([inbox / "orders.csv", inbox / "x.csv"], arch, "r1")
    assert moved[(inbox / "orders.csv").as_posix()].endswith("r1/orders_1.csv") and (arch / "r1" / "orders.csv").read_text() == "old"
    assert not list(inbox.iterdir())

def test_archive_files_validates_first(tmp_path):
    (tmp_path / "a.csv").write_text("a")
    with pytest.raises(FileNotFoundError):
        nb.archive_files([tmp_path / "a.csv", tmp_path / "nope.csv"], tmp_path / "arch", "r")
    assert (tmp_path / "a.csv").exists()


def test_sha256_file(tmp_path):
    import hashlib
    p = tmp_path / "a"; p.write_bytes(b"x" * 200_000)
    assert nb.sha256_file(p, chunk_size=1000) == hashlib.sha256(b"x" * 200_000).hexdigest()

def test_find_duplicate_files(tmp_path):
    (tmp_path / "d1").mkdir(); (tmp_path / "d2").mkdir()
    (tmp_path / "d1" / "a.csv").write_text("same"); (tmp_path / "d2" / "copy.csv").write_text("same")
    (tmp_path / "b.csv").write_text("diff"); (tmp_path / "e1").write_text(""); (tmp_path / "e2").write_text("")
    assert nb.find_duplicate_files(tmp_path) == [["d1/a.csv", "d2/copy.csv"]]

def test_find_duplicate_files_real():
    from pathlib import Path
    groups = nb.find_duplicate_files(Path(__file__).resolve().parents[2] / "datasets/daily")
    assert ["dt=2026-01-05/orders_20260105_part1.csv", "dt=2026-01-06/orders_20260105_part1_redelivered.csv"] in groups
