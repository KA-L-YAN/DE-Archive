"""Tests for 02_collections/01_lists.ipynb

Run: pytest tests/collections/test_02_01_lists.py -v
"""
import pytest

from labkit.testing import load

nb = load("02_collections/01_lists.ipynb")


@pytest.mark.parametrize("page, size, expected", [(1, 4, [0, 1, 2, 3]), (2, 4, [4, 5, 6, 7]), (3, 4, [8, 9]), (4, 4, []), (1, 100, list(range(10)))])
def test_paginate(page, size, expected):
    assert nb.paginate(list(range(10)), page, size) == expected

@pytest.mark.parametrize("page, size", [(0, 5), (1, 0), (-1, 3)])
def test_paginate_invalid(page, size):
    with pytest.raises(ValueError):
        nb.paginate([1, 2], page, size)


def test_chunk():
    assert nb.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert nb.chunk([1, 2], 5) == [[1, 2]]
    assert nb.chunk([], 3) == []

def test_chunk_large():
    batches = nb.chunk(list(range(10_001)), 500)
    assert len(batches) == 21 and len(batches[-1]) == 1 and sum(map(len, batches)) == 10_001

def test_chunk_invalid():
    with pytest.raises(ValueError):
        nb.chunk([1], 0)


def test_sort_orders():
    orders = [{"order_id": "B", "status": "SHIPPED", "amount": 10}, {"order_id": "A", "status": "FAILED", "amount": 5},
              {"order_id": "C", "status": "SHIPPED", "amount": 99}, {"order_id": "D", "status": "WEIRD", "amount": 1000},
              {"order_id": "A2", "status": "SHIPPED", "amount": 10}]
    original = [dict(o) for o in orders]
    result = nb.sort_orders(orders)
    assert [o["order_id"] for o in result] == ["A", "C", "A2", "B", "D"]
    assert orders == original

def test_sort_orders_empty():
    assert nb.sort_orders([]) == []


def test_flatten():
    assert nb.flatten([1, [2, (3, [4, ["five"]])], [], {"k": 1}]) == [1, 2, 3, 4, "five", {"k": 1}]

def test_flatten_edge():
    assert nb.flatten([]) == [] and nb.flatten([[[]]]) == [] and nb.flatten(["ab", b"cd"]) == ["ab", b"cd"]

def test_flatten_deep():
    deep = [1]
    for _ in range(200):
        deep = [deep, 2]
    assert len(nb.flatten(deep)) == 201


def test_merge_feeds():
    f1 = [{"event_id": 1, "ts": "2026-01-01T00:00:01"}, {"event_id": 3, "ts": "2026-01-01T00:00:03"}]
    f2 = [{"event_id": 2, "ts": "2026-01-01T00:00:02"}, {"event_id": 3, "ts": "2026-01-01T00:00:03"}, {"event_id": 4, "ts": "2026-01-01T00:00:03"}]
    assert [e["event_id"] for e in nb.merge_feeds([f1, f2])] == [1, 2, 3, 4]

def test_merge_feeds_ties_keep_feed_order():
    f1 = [{"event_id": "a", "ts": "t"}]
    f2 = [{"event_id": "b", "ts": "t"}]
    assert [e["event_id"] for e in nb.merge_feeds([f2, f1])] == ["b", "a"]

def test_merge_feeds_empty_and_large():
    assert nb.merge_feeds([]) == [] and nb.merge_feeds([[], []]) == []
    feeds = [[{"event_id": f"{k}-{i}", "ts": f"{i:08d}"} for i in range(k, 50_000, 3)] for k in range(3)]
    out = nb.merge_feeds(feeds)
    assert len(out) == 50_000 and [e["ts"] for e in out] == sorted(e["ts"] for e in out)
