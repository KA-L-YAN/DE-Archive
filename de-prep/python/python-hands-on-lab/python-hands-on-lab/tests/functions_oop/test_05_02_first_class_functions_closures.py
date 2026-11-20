"""Tests for 05_functions_and_oop/02_first_class_functions_closures.ipynb

Run: pytest tests/functions_oop/test_05_02_first_class_functions_closures.py -v
"""
import pytest

from labkit.testing import load

nb = load("05_functions_and_oop/02_first_class_functions_closures.ipynb")


def test_make_sequence():
    a, b = nb.make_sequence("ORD"), nb.make_sequence("INV", start=42, width=3)
    assert [a(), a(), b(), a()] == ["ORD000001", "ORD000002", "INV042", "ORD000003"]


def test_validators_closures():
    vs = [nb.required("id"), nb.max_length("name", 5), nb.one_of("status", "A", "B")]
    assert nb.check({"id": 1, "name": "Pavan", "status": "A"}, *vs) == []
    assert nb.check({"id": "", "name": "Kalyan", "status": "Z"}, *vs) == ["id is required", "name longer than 5", "status must be one of A, B"]
    assert nb.check({"id": 0}, *vs) == []

def test_late_binding_awareness():
    vs = [nb.required(f) for f in ["a", "b", "c"]]
    assert nb.check({"a": 1, "b": 1}, *vs) == ["c is required"]


def test_memoize():
    @nb.memoize
    def slow_square(x, power=2):
        "doc"
        return x ** power
    assert slow_square(3) == 9 and slow_square(3) == 9 and slow_square.calls == 1
    assert slow_square(3, power=3) == 27 and slow_square.calls == 2 and len(slow_square.cache) == 2
    assert slow_square.__name__ == "slow_square" and slow_square.__doc__ == "doc"

def test_memoize_kwargs_order_and_none_and_unhashable():
    @nb.memoize
    def f(a=0, b=0):
        return None
    f(a=1, b=2); f(b=2, a=1)
    assert f.calls == 1
    @nb.memoize
    def g(items):
        return len(items)
    assert g([1, 2]) == 2 and g([1, 2]) == 2 and g.calls == 2


class FakeClock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t

def test_rate_limiter():
    clock = FakeClock()
    allow = nb.make_rate_limiter(3, 10, clock=clock)
    assert [allow() for _ in range(4)] == [True, True, True, False] and allow.remaining() == 0
    clock.t = 9.99
    assert allow() is False
    clock.t = 10.0
    assert allow.remaining() == 3 and allow() is True and allow.remaining() == 2


def test_event_bus():
    sub, pub = nb.make_event_bus()
    seen = []
    def on_order(t, p): seen.append(("order", p))
    def on_all(t, p): seen.append(("all", t))
    def broken(t, p): raise RuntimeError("boom")
    un = sub("order.created", on_order); sub("*", on_all); sub("order.created", broken)
    r = pub("order.created", {"id": 1})
    assert seen == [("order", {"id": 1}), ("all", "order.created")]
    assert r["delivered"] == 2 and r["errors"][0][0] == "broken" and "boom" in r["errors"][0][1]
    un(); un()
    assert pub("order.created", 2)["delivered"] == 1
    assert pub("nothing", None) == {"delivered": 1, "errors": []}

def test_event_bus_unsubscribe_during_publish():
    sub, pub = nb.make_event_bus()
    calls = []
    holder = {}
    def once(t, p):
        calls.append("once"); holder["un"]()
    def other(t, p): calls.append("other")
    holder["un"] = sub("e", once); sub("e", other)
    pub("e", None); pub("e", None)
    assert calls == ["once", "other", "other"]
