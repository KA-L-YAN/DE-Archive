"""Tests for 03_pythonic_python/05_generators_iterators.ipynb

Run: pytest tests/pythonic/test_03_05_generators_iterators.py -v
"""
import pytest

from labkit.testing import load

nb = load("03_pythonic_python/05_generators_iterators.ipynb")


def test_read_lines(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("# header\n\n a \n  # indented comment\nb\n", encoding="utf-8")
    gen = nb.read_lines(p)
    assert iter(gen) is gen
    assert list(gen) == ["a", "b"]


def test_batched():
    assert list(nb.batched(range(5), 2)) == [(0, 1), (2, 3), (4,)]
    assert list(nb.batched([], 3)) == []
    assert list(nb.batched("abc", 5)) == [("a", "b", "c")]

def test_batched_infinite():
    from itertools import count
    assert next(iter(nb.batched(count(), 3))) == (0, 1, 2)

def test_batched_invalid():
    with pytest.raises(ValueError):
        list(nb.batched([1], 0))


def test_iter_jsonl():
    errors = []
    lines = ['{"a": 1}', "", '{"a": 2', "[1, 2]", '{"a": 3}']
    assert list(nb.iter_jsonl(lines, errors)) == [{"a": 1}, {"a": 3}]
    assert [n for n, _ in errors] == [3, 4]

def test_iter_jsonl_real_file():
    from pathlib import Path
    errors = []
    with open(Path(__file__).resolve().parents[2] / "datasets/json/events.jsonl", encoding="utf-8") as f:
        count = sum(1 for _ in nb.iter_jsonl(f, errors))
    assert count + len(errors) == 5000 and 10 < len(errors) < 120


def test_page_iterator_lazy():
    pages = {1: ["a", "b"], 2: ["c"]}
    calls = []
    def fetch(p):
        calls.append(p)
        return pages.get(p, [])
    it = nb.PageIterator(fetch)
    assert iter(it) is it and calls == []
    assert next(it) == "a" and calls == [1]
    assert list(it) == ["b", "c"] and it.pages_fetched == 3
    with pytest.raises(StopIteration):
        next(it)
    assert it.pages_fetched == 3

def test_page_iterator_start_page_and_empty():
    assert list(nb.PageIterator(lambda p: [p] if p < 5 else [], start_page=3)) == [3, 4]
    assert list(nb.PageIterator(lambda p: [])) == []


import json as _json

def _write(tmp_path, lines):
    p = tmp_path / "ev.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p

def test_event_stats_small(tmp_path):
    lines = [_json.dumps({"user_id": "u1", "ts": "2026-02-02T00:00:00Z", "event_type": "purchase", "properties": {"amount": 10.555}}),
             _json.dumps({"user_id": "u2", "ts": "2026-02-01T00:00:00Z", "event_type": "login"}),
             _json.dumps({"user_id": None, "ts": "2026-02-03T00:00:00Z", "event_type": "login"}),
             '{"user_id": "u3", "ts"', "", _json.dumps({"user_id": "u1", "ts": "2026-02-05T00:00:00Z", "event_type": "login"})]
    s = nb.event_stats(_write(tmp_path, lines))
    assert (s["lines"], s["malformed"], s["invalid"], s["valid"]) == (5, 1, 1, 3)
    assert s["by_type"] == {"login": 2, "purchase": 1} and s["active_users"] == 2
    assert s["first_ts"] == "2026-02-01T00:00:00Z" and s["last_ts"] == "2026-02-05T00:00:00Z"
    assert s["purchase_revenue"] in (10.55, 10.56)

def test_event_stats_empty(tmp_path):
    s = nb.event_stats(_write(tmp_path, [""]))
    assert s["valid"] == 0 and s["first_ts"] is None and s["by_type"] == {}

def test_event_stats_real_and_large(tmp_path):
    from pathlib import Path
    real = nb.event_stats(Path(__file__).resolve().parents[2] / "datasets/json/events.jsonl")
    assert real["lines"] == 5000 and real["valid"] + real["invalid"] + real["malformed"] == 5000
    big = [_json.dumps({"user_id": f"u{i % 1000}", "ts": f"2026-01-01T00:00:{i % 60:02d}Z", "event_type": "page_view"}) for i in range(200_000)]
    s = nb.event_stats(_write(tmp_path, big))
    assert s["valid"] == 200_000 and s["active_users"] == 1000
