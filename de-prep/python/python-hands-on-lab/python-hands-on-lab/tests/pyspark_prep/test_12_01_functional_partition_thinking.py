"""Tests for 12_pyspark_preparation/01_functional_partition_thinking.ipynb

Run: pytest tests/pyspark_prep/test_12_01_functional_partition_thinking.py -v
"""
import pytest

from labkit.testing import load

nb = load("12_pyspark_preparation/01_functional_partition_thinking.ipynb")


def test_word_count_phases():
    lines = ["Spark is fast.", "Python is fun, spark is FAST!", ""]
    pairs = list(nb.map_phase(lines))
    assert pairs[:3] == [("spark", 1), ("is", 1), ("fast", 1)] and len(pairs) == 9
    groups = nb.shuffle_phase(pairs)
    assert groups["is"] == [1, 1, 1]
    assert nb.reduce_phase(groups) == {"spark": 2, "is": 3, "fast": 2, "python": 1, "fun": 1}


def test_partitioned_sum():
    recs = [{"country": c, "amt": 1.0} for c in ["IN", "FI", "SE"] * 1000]
    with_c, shuffled_c = nb.partitioned_sum(recs, "country", "amt", 4, use_combiner=True)
    without, shuffled = nb.partitioned_sum(recs, "country", "amt", 4, use_combiner=False)
    assert with_c == without == {"FI": 1000.0, "IN": 1000.0, "SE": 1000.0}
    assert shuffled == 3000 and shuffled_c <= 12


def test_transform():
    rows = [{"id": 1, "q": 2, "p": 10.0}, {"id": 2, "q": 0, "p": 5.0}]
    steps = [("with_column", "amount", lambda r: r["q"] * r["p"]), ("filter", lambda r: r["amount"] > 0),
             ("rename", {"q": "quantity"}), ("drop", ["p"]), ("select", ["id", "quantity", "amount"])]
    assert nb.transform(rows, steps) == [{"id": 1, "quantity": 2, "amount": 20.0}] and rows[0] == {"id": 1, "q": 2, "p": 10.0}
    with pytest.raises(KeyError):
        nb.transform(rows, [("select", ["nope"])])
    with pytest.raises(ValueError):
        nb.transform(rows, [("explode", "x")])


def test_joins_agree():
    orders = [{"oid": i, "cid": f"C{i % 50}"} for i in range(1000)]
    customers = [{"cid": f"C{i}", "seg": "smb" if i % 2 else "retail"} for i in range(40)] + [{"cid": "C1", "seg": "dup"}]
    b = nb.broadcast_join(orders, customers, "cid")
    s, sizes = nb.shuffle_join(orders, customers, "cid", 4)
    key = lambda r: (r["oid"], r["seg"])
    assert sorted(b, key=key) == sorted(s, key=key) and len(b) == 800 + 20 and sum(sizes) == len(s) and len(sizes) == 4


def test_salted_join():
    left = [{"oid": i, "cid": "HOT" if i % 10 else f"C{i}"} for i in range(4000)]
    right = [{"cid": "HOT", "name": "BigCo"}] + [{"cid": f"C{i}", "name": f"n{i}"} for i in range(0, 4000, 10)]
    from collections import defaultdict
    idx = defaultdict(list)
    for r in right: idx[r["cid"]].append(r)
    expected = sorted(({**l, **r} for l in left for r in idx[l["cid"]]), key=lambda r: r["oid"])
    rows, sizes = nb.salted_join(left, right, "cid", n=8, hot_keys={"HOT"}, salt_buckets=8)
    assert sorted(rows, key=lambda r: r["oid"]) == expected and len(sizes) == 8
    assert max(sizes) < 0.4 * len(expected)
