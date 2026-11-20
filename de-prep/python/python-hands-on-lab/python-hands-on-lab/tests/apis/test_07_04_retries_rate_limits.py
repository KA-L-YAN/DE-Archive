"""Tests for 07_apis/04_retries_rate_limits.ipynb

Run: pytest tests/apis/test_07_04_retries_rate_limits.py -v
"""
import pytest

from labkit.testing import load
from labkit.mock_api import MockSession, BASE_URL
import requests

nb = load("07_apis/04_retries_rate_limits.ipynb")


@pytest.mark.parametrize("o, expected", [(429, True), (503, True), (500, True), (404, False), (422, False), (200, False),
                                         (requests.Timeout(), True), (requests.ConnectionError(), True), (TimeoutError(), True), (ValueError(), False), (True, False)])
def test_is_retryable(o, expected):
    assert nb.is_retryable(o) is expected


def test_backoff_delays():
    assert nb.backoff_delays(5) == [0.5, 1.0, 2.0, 4.0, 8.0]
    assert nb.backoff_delays(4, base=1, factor=3, max_delay=10) == [1, 3, 9, 10]
    assert nb.backoff_delays(3, jitter=lambda d: d / 2) == [0.25, 0.5, 1.0] and nb.backoff_delays(0) == []


def test_parse_retry_after():
    from datetime import datetime, timezone
    now = datetime(2026, 10, 21, 7, 27, 0, tzinfo=timezone.utc)
    assert nb.parse_retry_after("120") == 120.0 and nb.parse_retry_after(" 0 ") == 0.0
    assert nb.parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT", now=now) == 60.0
    assert nb.parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=now) == 0.0
    assert nb.parse_retry_after(None) is None and nb.parse_retry_after("soon") is None and nb.parse_retry_after("-5") is None


def test_get_with_retry_recovers(no_sleep):
    s = MockSession(data={"customers": [{"customer_id": "C1"}]}, faults={"/customers": ["timeout", 503, 429, None]})
    r = nb.get_with_retry(s, f"{BASE_URL}/customers", params={"page": 1}, sleep=no_sleep)
    assert r.status_code == 200 and nb.get_with_retry.last_attempts == 4 and no_sleep.calls == [0.5, 1.0, 1.0]

def test_get_with_retry_gives_up(no_sleep):
    s = MockSession(data={"customers": []}, faults={"/customers": [500, 500, 500]})
    with pytest.raises(requests.HTTPError):
        nb.get_with_retry(s, f"{BASE_URL}/customers", max_attempts=3, sleep=no_sleep)
    assert len(s.calls) == 3 and len(no_sleep.calls) == 2

def test_get_with_retry_non_retryable_and_exception(no_sleep):
    s = MockSession(data={"customers": []})
    with pytest.raises(requests.HTTPError):
        nb.get_with_retry(s, f"{BASE_URL}/customers/none", sleep=no_sleep)
    assert no_sleep.calls == []
    s2 = MockSession(data={"customers": []}, faults={"/customers": ["connection", "connection"]})
    with pytest.raises(requests.ConnectionError):
        nb.get_with_retry(s2, f"{BASE_URL}/customers", max_attempts=2, sleep=no_sleep)


class Time:
    def __init__(self): self.t = 0.0; self.sleeps = []
    def clock(self): return self.t
    def sleep(self, s): self.sleeps.append(s); self.t += s

def test_token_bucket_throttles():
    tm = Time()
    s = MockSession(data={"customers": [{"customer_id": "C1"}]})
    c = nb.ResilientClient(s, BASE_URL, rate_per_sec=2, burst=2, clock=tm.clock, sleep=tm.sleep)
    for _ in range(4):
        c.get("customers/C1")
    assert c.metrics["requests"] == 4 and c.metrics["throttled_waits"] == 2 and tm.t == pytest.approx(1.0)

def test_retries_then_success():
    tm = Time()
    s = MockSession(data={"customers": [{"customer_id": "C1"}]}, faults={"/customers/C1": [503, "timeout"]})
    c = nb.ResilientClient(s, BASE_URL, clock=tm.clock, sleep=tm.sleep)
    assert c.get("customers/C1") == {"customer_id": "C1"} and c.metrics["retries"] == 2 and c.consecutive_failures == 0

def test_circuit_breaker_opens_and_recovers():
    tm = Time()
    s = MockSession(data={"customers": [{"customer_id": "C1"}]}, faults={"/customers/C1": [500] * 6})
    c = nb.ResilientClient(s, BASE_URL, max_attempts=3, failure_threshold=2, cooldown=30, clock=tm.clock, sleep=tm.sleep)
    for _ in range(2):
        with pytest.raises(requests.HTTPError):
            c.get("customers/C1")
    calls_before = len(s.calls)
    with pytest.raises(nb.CircuitOpen):
        c.get("customers/C1")
    assert len(s.calls) == calls_before and c.metrics["circuit_rejections"] == 1
    tm.t += 31
    assert c.get("customers/C1") == {"customer_id": "C1"} and c.opened_at is None

def test_404_does_not_trip_breaker():
    tm = Time()
    s = MockSession(data={"customers": []})
    c = nb.ResilientClient(s, BASE_URL, failure_threshold=1, clock=tm.clock, sleep=tm.sleep)
    with pytest.raises(requests.HTTPError):
        c.get("customers/X")
    assert c.opened_at is None and c.consecutive_failures == 0
