"""Tests for 05_functions_and_oop/03_decorators.ipynb

Run: pytest tests/functions_oop/test_05_03_decorators.py -v
"""
import pytest

from labkit.testing import load
import logging

nb = load("05_functions_and_oop/03_decorators.ipynb")


def test_timed():
    @nb.timed
    def add(a, b=1):
        return a + b
    assert add.last_duration is None
    assert add(1, b=2) == 3 and add.last_duration >= 0 and len(add.durations) == 1 and add.__name__ == "add"
    @nb.timed
    def boom():
        raise ValueError("x")
    with pytest.raises(ValueError):
        boom()
    assert boom.last_duration is not None


def test_log_calls(caplog):
    logger = logging.getLogger("lab.test.decorators")
    @nb.log_calls(logger)
    def add(a, b=0):
        return a + b
    with caplog.at_level(logging.DEBUG, logger="lab.test.decorators"):
        assert add(2, b=3) == 5
    msgs = [r.getMessage() for r in caplog.records]
    assert msgs == ["calling add args=(2,) kwargs={'b': 3}", "add returned 5"]

def test_log_calls_error(caplog):
    logger = logging.getLogger("lab.test.decorators2")
    @nb.log_calls(logger, level=logging.INFO)
    def fail():
        raise KeyError("k")
    with caplog.at_level(logging.INFO, logger="lab.test.decorators2"):
        with pytest.raises(KeyError):
            fail()
    err = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(err) == 1 and "fail raised KeyError" in err[0].getMessage() and err[0].exc_info


def test_validate_args():
    @nb.validate_args(batch_size=lambda n: n > 0, env=lambda e: e in {"dev", "prod"})
    def run(env, batch_size=100):
        return env, batch_size
    assert run("dev") == ("dev", 100) and run("prod", 5) == ("prod", 5) and run(batch_size=1, env="dev") == ("dev", 1)
    with pytest.raises(ValueError, match="batch_size: 0"):
        run("dev", 0)
    with pytest.raises(ValueError, match="env"):
        run(env="qa")

def test_validate_args_bad_default_and_unknown():
    @nb.validate_args(n=lambda n: n > 0)
    def f(n=0):
        return n
    with pytest.raises(ValueError):
        f()
    with pytest.raises(TypeError):
        nb.validate_args(missing=bool)(lambda x: x)


def test_retry_succeeds_after_failures(no_sleep):
    state = {"n": 0}
    @nb.retry(times=4, exceptions=(ConnectionError,), delay=1, backoff=2, max_delay=3, sleep=no_sleep)
    def flaky():
        state["n"] += 1
        if state["n"] < 4:
            raise ConnectionError("down")
        return "ok"
    assert flaky() == "ok" and flaky.last_attempts == 4 and no_sleep.calls == [1, 2, 3]

def test_retry_gives_up_and_reraises(no_sleep):
    @nb.retry(times=2, exceptions=(TimeoutError,), delay=0.5, sleep=no_sleep)
    def always():
        raise TimeoutError("slow")
    with pytest.raises(TimeoutError):
        always()
    assert always.last_attempts == 2 and no_sleep.calls == [0.5]

def test_retry_other_exception_immediate(no_sleep):
    @nb.retry(times=5, exceptions=(ConnectionError,), sleep=no_sleep)
    def bug():
        raise KeyError("x")
    with pytest.raises(KeyError):
        bug()
    assert bug.last_attempts == 1 and no_sleep.calls == []

def test_retry_invalid():
    with pytest.raises(ValueError):
        nb.retry(times=0)


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t

def test_ttl_cache_expiry():
    clock, calls = Clock(), []
    @nb.ttl_cache(ttl=10, clock=clock)
    def token(user):
        calls.append(user); return f"tok-{user}-{len(calls)}"
    assert token("k") == "tok-k-1" and token("k") == "tok-k-1"
    clock.t = 9.9
    assert token("k") == "tok-k-1"
    clock.t = 10
    assert token("k") == "tok-k-2"
    assert token.cache_info() == {"hits": 2, "misses": 2, "size": 1}

def test_ttl_cache_lru_and_clear():
    clock = Clock()
    @nb.ttl_cache(ttl=100, maxsize=2, clock=clock)
    def sq(x):
        return x * x
    sq(1); sq(2); sq(1); sq(3)
    assert sq.cache_info()["size"] == 2
    misses = sq.cache_info()["misses"]
    sq(1)
    assert sq.cache_info()["misses"] == misses
    sq(2)
    assert sq.cache_info()["misses"] == misses + 1
    sq.cache_clear()
    assert sq.cache_info() == {"hits": 0, "misses": 0, "size": 0}
