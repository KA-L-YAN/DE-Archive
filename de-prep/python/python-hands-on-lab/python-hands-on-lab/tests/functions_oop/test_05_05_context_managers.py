"""Tests for 05_functions_and_oop/05_context_managers.ipynb

Run: pytest tests/functions_oop/test_05_05_context_managers.py -v
"""
import pytest

from labkit.testing import load

nb = load("05_functions_and_oop/05_context_managers.ipynb")


def test_timer():
    with nb.Timer("x") as t:
        assert t.elapsed is None
        sum(range(1000))
    assert t.elapsed >= 0 and t.label == "x"

def test_timer_does_not_suppress():
    t = nb.Timer()
    with pytest.raises(ZeroDivisionError):
        with t:
            1 / 0
    assert t.elapsed is not None


def test_working_directory(tmp_path):
    import os
    from pathlib import Path
    start = Path.cwd()
    with nb.working_directory(tmp_path / "a" / "b") as p:
        assert Path.cwd() == (tmp_path / "a" / "b").resolve() and p == tmp_path / "a" / "b"
    assert Path.cwd() == start
    class Boom(Exception):
        pass
    with pytest.raises(Boom):
        with nb.working_directory(tmp_path):
            raise Boom
    assert Path.cwd() == start


def test_temp_env(monkeypatch):
    import os
    monkeypatch.setenv("LAB_EXISTING", "old")
    monkeypatch.delenv("LAB_NEW", raising=False)
    with nb.temp_env(LAB_EXISTING="new", LAB_NEW=5, LAB_GONE=None):
        assert os.environ["LAB_EXISTING"] == "new" and os.environ["LAB_NEW"] == "5" and "LAB_GONE" not in os.environ
    assert os.environ["LAB_EXISTING"] == "old" and "LAB_NEW" not in os.environ
    with pytest.raises(ValueError):
        with nb.temp_env(LAB_EXISTING=None):
            assert "LAB_EXISTING" not in os.environ
            raise ValueError
    assert os.environ["LAB_EXISTING"] == "old"


def test_kv_commit():
    s = nb.KeyValueStore()
    s.set("a", 1)
    with s.transaction():
        s.set("b", 2); s.delete("a")
        assert s.get("b") == 2 and s.get("a") is None and s.committed() == {"a": 1}
    assert s.committed() == {"b": 2} and (s.commits, s.rollbacks) == (1, 0)

def test_kv_rollback_and_nested():
    s = nb.KeyValueStore()
    s.set("a", 1)
    with pytest.raises(ValueError):
        with s.transaction():
            s.set("a", 100)
            raise ValueError("abort")
    assert s.get("a") == 1 and s.rollbacks == 1
    with pytest.raises(RuntimeError):
        with s.transaction():
            with s.transaction():
                pass
    s.set("c", 3)
    assert s.committed()["c"] == 3


import csv as _csv

def _write(path, rows, header=("id", "ts")):
    with open(path, "w", newline="") as f:
        w = _csv.writer(f); w.writerow(header); w.writerows(rows)

def test_merge_sorted_files(tmp_path):
    _write(tmp_path / "a.csv", [("1", "01"), ("4", "04"), ("6", "06")])
    _write(tmp_path / "b.csv", [("2", "02"), ("3", "03")])
    _write(tmp_path / "c.csv", [])
    n = nb.merge_sorted_files([tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "c.csv"], tmp_path / "out" / "m.csv", "ts")
    lines = (tmp_path / "out" / "m.csv").read_text().splitlines()
    assert n == 5 and lines[0] == "id,ts" and [l.split(",")[0] for l in lines[1:]] == ["1", "2", "3", "4", "6"]

def test_merge_sorted_files_header_mismatch(tmp_path):
    _write(tmp_path / "a.csv", [("1", "01")])
    _write(tmp_path / "b.csv", [("1", "01")], header=("id", "other"))
    with pytest.raises(ValueError):
        nb.merge_sorted_files([tmp_path / "a.csv", tmp_path / "b.csv"], tmp_path / "m.csv", "ts")
    assert not (tmp_path / "m.csv").exists()

def test_merge_sorted_files_missing_input_and_empty(tmp_path):
    _write(tmp_path / "a.csv", [("1", "01")])
    with pytest.raises(FileNotFoundError):
        nb.merge_sorted_files([tmp_path / "a.csv", tmp_path / "missing.csv"], tmp_path / "m.csv", "ts")
    assert nb.merge_sorted_files([], tmp_path / "m.csv", "ts") == 0
