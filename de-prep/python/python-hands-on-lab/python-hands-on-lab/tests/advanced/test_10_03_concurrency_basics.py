"""Tests for 10_advanced_python/03_concurrency_basics.ipynb

Run: pytest tests/advanced/test_10_03_concurrency_basics.py -v
"""
import pytest

from labkit.testing import load
import time
import threading

nb = load("10_advanced_python/03_concurrency_basics.ipynb")


def test_thread_map_order_and_speed():
    def slow_square(x):
        time.sleep(0.1)
        return x * x
    thread_map = nb.thread_map          # load the notebook before timing
    start = time.perf_counter()
    assert thread_map(slow_square, range(16), max_workers=16) == [x * x for x in range(16)]
    assert time.perf_counter() - start < 0.8   # sequential would take 1.6s

def test_thread_map_exception():
    def boom(x):
        if x == 3:
            raise ValueError("bad 3")
        return x
    with pytest.raises(ValueError, match="bad 3"):
        nb.thread_map(boom, range(5))


def test_safe_counter_threads():
    c = nb.SafeCounter()
    def hammer():
        for _ in range(5000):
            c.add("x")
            time.sleep(0)
    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert c.snapshot() == {"x": 40_000}

def test_count_events_concurrently():
    batches = [["view", "click"] * 500, ["view"] * 1000, ["buy"]] * 10
    assert nb.count_events_concurrently(batches) == {"view": 15_000, "click": 5_000, "buy": 10}


def test_parallel_checksums(tmp_path):
    import hashlib
    files = []
    for i in range(12):
        p = tmp_path / f"f{i}.bin"; p.write_bytes(bytes([i]) * (1000 + i)); files.append(p)
    out = nb.parallel_checksums(files, workers=2)
    assert out == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert nb.parallel_checksums([]) == {}


def test_fetch_all_bounded():
    import asyncio
    state = {"current": 0, "peak": 0}
    async def fake_fetch(i):
        state["current"] += 1
        state["peak"] = max(state["peak"], state["current"])
        await asyncio.sleep(0.01)
        state["current"] -= 1
        if i == 7:
            raise ValueError("boom 7")
        return i * 2
    fetch_all = nb.fetch_all
    start = time.perf_counter()
    results = asyncio.run(fetch_all(fake_fetch, list(range(50)), concurrency=5))
    elapsed = time.perf_counter() - start
    assert state["peak"] == 5 and isinstance(results[7], ValueError) and results[:3] == [0, 2, 4] and results[49] == 98
    assert elapsed < 0.5


def test_threaded_pipeline():
    def download(x):
        time.sleep(0.001)
        return x * 2
    def parse(x):
        if x == 14:
            raise ValueError("cannot parse 14")
        return x + 1
    results, errors = nb.run_threaded_pipeline(range(100), [download, parse], workers_per_stage=4, queue_size=5)
    assert sorted(results) == sorted(x * 2 + 1 for x in range(100) if x != 7)
    assert errors == [(7, 1, "ValueError: cannot parse 14")]
    assert threading.active_count() < 10

def test_threaded_pipeline_empty_and_single_stage():
    assert nb.run_threaded_pipeline([], [lambda x: x]) == ([], [])
    res, err = nb.run_threaded_pipeline(["a", "b"], [str.upper], workers_per_stage=1)
    assert sorted(res) == ["A", "B"] and err == []
