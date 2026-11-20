"""Tests for 10_advanced_python/01_generators_itertools.ipynb

Run: pytest tests/advanced/test_10_01_generators_itertools.py -v
"""
import pytest

from labkit.testing import load

nb = load("10_advanced_python/01_generators_itertools.ipynb")


def test_running_max():
    assert list(nb.running_max([3, 1, 4, 1, 5])) == [3, 3, 4, 4, 5] and list(nb.running_max([])) == []
    from itertools import count, islice
    assert list(islice(nb.running_max(count()), 3)) == [0, 1, 2]


def test_windowed():
    assert list(nb.windowed([1, 2, 3, 4], 3)) == [(1, 2, 3), (2, 3, 4)] and list(nb.windowed([1, 2], 3)) == []
    assert list(nb.windowed("abc", 1)) == [("a",), ("b",), ("c",)]
    with pytest.raises(ValueError):
        nb.windowed([1], 0)


def test_status_runs():
    ev = [{"ts": "t1", "status": "UP"}, {"ts": "t2", "status": "UP"}, {"ts": "t3", "status": "DOWN"}, {"ts": "t4", "status": "UP"}]
    assert nb.status_runs(ev) == [("UP", 2, "t1", "t2"), ("DOWN", 1, "t3", "t3"), ("UP", 1, "t4", "t4")] and nb.status_runs([]) == []


def test_merge_join():
    left = [{"k": 1, "l": "a"}, {"k": 2, "l": "b"}, {"k": 2, "l": "c"}, {"k": 4, "l": "d"}]
    right = [{"k": 0, "r": "z"}, {"k": 2, "r": "x"}, {"k": 2, "r": "y"}, {"k": 3, "r": "w"}, {"k": 4, "r": "v"}]
    pairs = [(l["l"], r["r"]) for l, r in nb.merge_join(iter(left), iter(right), key=lambda d: d["k"])]
    assert pairs == [("b", "x"), ("b", "y"), ("c", "x"), ("c", "y"), ("d", "v")]
    assert list(nb.merge_join([], right, key=lambda d: d["k"])) == []

def test_merge_join_unsorted():
    with pytest.raises(ValueError):
        list(nb.merge_join([{"k": 2}, {"k": 1}], [{"k": 1}, {"k": 2}], key=lambda d: d["k"]))

def test_merge_join_large_streaming():
    left = ({"k": i} for i in range(0, 200_000, 2))
    right = ({"k": i} for i in range(0, 200_000, 3))
    assert sum(1 for _ in nb.merge_join(left, right, key=lambda d: d["k"])) == len(range(0, 200_000, 6))


def test_stream_lazy_and_chainable():
    calls = []
    def src():
        for i in range(10):
            calls.append(i)
            yield i
    s = nb.Stream(src).map(lambda x: x * 10).filter(lambda x: x % 20 == 0)
    assert calls == []
    assert s.collect() == [0, 20, 40, 60, 80] and s.count() == 5 and len(calls) == 20
    assert s.take(2).collect() == [0, 20]

def test_stream_infinite_and_branching():
    from itertools import count
    base = nb.Stream(lambda: count())
    evens, odds = base.filter(lambda x: x % 2 == 0), base.filter(lambda x: x % 2)
    assert evens.take(3).collect() == [0, 2, 4] and odds.take(2).collect() == [1, 3]

def test_stream_other_ops():
    words = nb.Stream(["a b", "b c", "a"]).flat_map(str.split)
    assert words.collect() == ["a", "b", "b", "c", "a"] and words.distinct().collect() == ["a", "b", "c"]
    assert nb.Stream(range(7)).batch(3).collect() == [[0, 1, 2], [3, 4, 5], [6]]
    assert nb.Stream(range(5)).reduce(lambda a, x: a + x, 0) == 10 and nb.Stream([]).first("none") == "none"
    assert nb.Stream(["ab", "cd", "aef"]).group_by_key(lambda s: s[0], len) == {"a": [2, 3], "c": [2]}

def test_stream_one_shot_source():
    s = nb.Stream(iter([1, 2, 3]))
    assert s.collect() == [1, 2, 3] and s.collect() == []
