"""Tests for 00_diagnostic/diagnostic_01_core_python.ipynb

Run: pytest tests/diagnostic/test_00_diagnostic_01_core_python.py -v
"""
import pytest

from labkit.testing import load

nb = load("00_diagnostic/diagnostic_01_core_python.ipynb")


@pytest.mark.parametrize("text, secs", [("1h30m15s", 5415), ("45m", 2700), ("2h", 7200), ("90s", 90), ("1H5S", 3605), ("0s", 0)])
def test_q1_parse_duration(text, secs):
    assert nb.parse_duration(text) == secs

@pytest.mark.parametrize("bad", ["", "1x", "30s1h", "h", "1h 30m", "-5s"])
def test_q1_parse_duration_invalid(bad):
    with pytest.raises(ValueError):
        nb.parse_duration(bad)


@pytest.mark.parametrize("ip, ok", [("192.168.0.1", True), ("0.0.0.0", True), ("255.255.255.255", True), ("256.1.1.1", False), ("01.2.3.4", False),
                                    ("1.2.3", False), ("1.2.3.4.5", False), ("1.2.3.-4", False), ("1.2. 3.4", False), ("a.b.c.d", False), ("", False), ("1.2.3.²", False)])
def test_q2_is_ipv4(ip, ok):
    assert nb.is_ipv4(ip) is ok


@pytest.mark.parametrize("a, b, r", [("1.10.0", "1.9", 1), ("1.2", "1.2.0", 0), ("v2.0", "2.0.1", -1), ("10", "9.99", 1), ("0.0.1", "0", 1)])
def test_q3_compare_versions(a, b, r):
    assert nb.compare_versions(a, b) == r and nb.compare_versions(b, a) == -r

def test_q3_compare_versions_invalid():
    with pytest.raises(ValueError):
        nb.compare_versions("1.x", "1.0")


def test_q4_wrap():
    assert nb.wrap("the quick brown fox jumps", 10) == ["the quick", "brown fox", "jumps"]
    assert nb.wrap("supercalifragilistic is long", 6) == ["superc", "alifra", "gilist", "ic is", "long"]
    assert nb.wrap("   ", 5) == [] and nb.wrap("a b c", 1) == ["a", "b", "c"]
    with pytest.raises(ValueError):
        nb.wrap("x", 0)
