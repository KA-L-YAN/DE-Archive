"""Tests for 00_diagnostic/diagnostic_03_pythonic.ipynb

Run: pytest tests/diagnostic/test_00_diagnostic_03_pythonic.py -v
"""
import pytest

from labkit.testing import load

nb = load("00_diagnostic/diagnostic_03_pythonic.ipynb")


def test_q1_transpose():
    assert nb.transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]] and nb.transpose([]) == [] and nb.transpose([[1]]) == [[1]]


def test_q2_first_repeat():
    from itertools import count, chain
    assert nb.first_repeat([3, 1, 4, 1, 5, 3]) == 1 and nb.first_repeat([]) is None and nb.first_repeat("abc") is None
    assert nb.first_repeat(chain([7, 8], count())) == 7


def test_q3_group_anagrams():
    assert nb.group_anagrams(["listen", "Silent", "enlist", "google", "gooegl", "cat", "act", "tac"]) == [["listen", "Silent", "enlist"], ["google", "gooegl"], ["cat", "act", "tac"]]
    assert nb.group_anagrams([]) == []


def test_q4_balances():
    pairs, od = nb.balances(100, [("t1", -30), ("t2", -80.5), ("t3", 20), ("t4", -50)])
    assert pairs == [("t1", 70), ("t2", -10.5), ("t3", 9.5), ("t4", -40.5)] and od == "t2"
    assert nb.balances(5, []) == ([], None) and nb.balances(0, [("a", 1)])[1] is None
