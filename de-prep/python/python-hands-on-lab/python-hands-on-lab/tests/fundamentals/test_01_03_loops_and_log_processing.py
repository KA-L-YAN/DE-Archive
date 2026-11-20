"""Tests for 01_python_fundamentals/03_loops_and_log_processing.ipynb

Run: pytest tests/fundamentals/test_01_03_loops_and_log_processing.py -v
"""
import pytest

from labkit.testing import load
from datetime import datetime as dt
from datetime import datetime as dt, timedelta as td

nb = load("01_python_fundamentals/03_loops_and_log_processing.ipynb")


def test_count_levels():
    lines = ["2026-03-01T00:00:01Z INFO [x] a", "", "Traceback (most recent call last):",
             "2026-03-01T00:00:02Z ERROR [y] b", "2026-03-01T00:00:03Z INFO [x] c", "2026"]
    assert nb.count_levels(lines) == {"INFO": 2, "ERROR": 1}

def test_count_levels_empty():
    assert nb.count_levels([]) == {}


def test_find_slow_requests():
    lines = ['2026 INFO [s] req=a1 status=200 latency_ms=1500 msg="x"', '2026 INFO [s] req=b2 latency_ms=20',
             'no fields here', '2026 INFO [s] latency_ms=5000', '2026 INFO [s] req=c3 latency_ms=abc', '2026 INFO [s] req=d4 latency_ms=1000']
    assert nb.find_slow_requests(lines, 1000) == [("a1", 1500)]

def test_find_slow_requests_none():
    assert nb.find_slow_requests([], 10) == []


def test_merge_multiline():
    lines = ["  orphan continuation", "2026-03-01T00:00:01Z ERROR boom", "Traceback (most recent call last):", "",
             "ValueError: x", "2026-03-01T00:00:02Z INFO ok"]
    assert nb.merge_multiline(lines) == ["2026-03-01T00:00:01Z ERROR boom\nTraceback (most recent call last):\nValueError: x",
                                         "2026-03-01T00:00:02Z INFO ok"]

def test_merge_multiline_empty():
    assert nb.merge_multiline([]) == [] and nb.merge_multiline(["", "x"]) == []


def test_count_sessions():
    ev = [("u1", dt(2026, 1, 1, 11, 0)), ("u1", dt(2026, 1, 1, 10, 0)), ("u2", dt(2026, 1, 1, 9, 0)), ("u1", dt(2026, 1, 1, 10, 20))]
    assert nb.count_sessions(ev) == {"u1": 2, "u2": 1}

def test_count_sessions_boundary():
    ev = [("u", dt(2026, 1, 1, 10, 0)), ("u", dt(2026, 1, 1, 10, 30)), ("u", dt(2026, 1, 1, 11, 0, 1))]
    assert nb.count_sessions(ev) == {"u": 2}
    assert nb.count_sessions(ev, gap_minutes=60) == {"u": 1}

def test_count_sessions_empty():
    assert nb.count_sessions([]) == {}


T0 = dt(2026, 3, 1, 12, 0, 0)

def test_error_bursts_fires_once_per_burst():
    entries = [(T0 + td(seconds=i * 10), "ERROR") for i in range(6)] + [(T0 + td(seconds=65), "INFO")]
    assert nb.error_bursts(entries, window_seconds=60, threshold=5) == [T0 + td(seconds=40)]

def test_error_bursts_window_edge():
    entries = [(T0, "ERROR"), (T0 + td(seconds=60), "ERROR")]
    assert nb.error_bursts(entries, window_seconds=60, threshold=2) == []
    assert nb.error_bursts(entries, window_seconds=61, threshold=2) == [T0 + td(seconds=60)]

def test_error_bursts_ignores_info_and_counts_critical():
    entries = [(T0, "CRITICAL"), (T0 + td(seconds=1), "INFO"), (T0 + td(seconds=2), "ERROR")]
    assert nb.error_bursts(entries, threshold=2) == [T0 + td(seconds=2)]

def test_error_bursts_large_input():
    entries = [(T0 + td(seconds=i), "ERROR") for i in range(100_000)]
    assert len(nb.error_bursts(entries, window_seconds=60, threshold=5)) == 20_000
