"""Tests for 10_advanced_python/02_typing_dataclasses_enums.ipynb

Run: pytest tests/advanced/test_10_02_typing_dataclasses_enums.py -v
"""
import pytest

from labkit.testing import load
from decimal import Decimal

nb = load("10_advanced_python/02_typing_dataclasses_enums.ipynb")


def test_order_status():
    S = nb.OrderStatus
    assert S.parse(" shipped ") is S.SHIPPED and S.SHIPPED == "SHIPPED" and S.DELIVERED.is_terminal and not S.PLACED.is_terminal
    with pytest.raises(ValueError, match="PLACED"):
        S.parse("lost")
    import json
    assert json.dumps({"s": S.PLACED}) == '{"s": "PLACED"}' and [m.value for m in S][0] == "PLACED"


def test_order_line():
    a = nb.OrderLine.from_dict({"order_id": "O2", "line_no": "1", "product_id": "P1", "quantity": "3", "unit_price": "10.50"})
    b = nb.OrderLine("O1", 2, "P2", 1, 5)
    assert a.unit_price == Decimal("10.50") and a.amount == Decimal("31.50") and b.unit_price == Decimal("5")
    assert sorted([a, b, nb.OrderLine("O1", 1, "P3", 1, "1")])[0].line_no == 1 and len({a, a}) == 1
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.quantity = 5
    with pytest.raises(AttributeError):
        object.__getattribute__(a, "__dict__")

@pytest.mark.parametrize("kw", [dict(line_no=0), dict(quantity=0), dict(unit_price="-1"), dict(order_id=" ")])
def test_order_line_validation(kw):
    base = dict(order_id="O", line_no=1, product_id="P", quantity=1, unit_price="1")
    with pytest.raises(ValueError):
        nb.OrderLine(**{**base, **kw})

def test_order_line_float_rejected():
    with pytest.raises(TypeError):
        nb.OrderLine("O", 1, "P", 1, 0.1)


def test_read_lines(tmp_path):
    import io
    p = tmp_path / "a.txt"; p.write_text(" x \n\n y\n")
    assert nb.read_lines(p) == ["x", "y"] and nb.read_lines("a\n b \n") == ["a", "b"] and nb.read_lines(b"q\nr") == ["q", "r"]
    assert nb.read_lines(io.StringIO("1\n\n2")) == ["1", "2"] and nb.read_lines(["  m", "", "n "]) == ["m", "n"]
    with open(p) as f:
        assert nb.read_lines(f) == ["x", "y"]


import dataclasses as _dc
from datetime import date as _date, datetime as _datetime
from decimal import Decimal as _Decimal
from enum import Enum as _Enum

class Channel(_Enum):
    WEB = "web"
    APP = "app"

@_dc.dataclass
class Row:
    order_id: str
    quantity: int
    price: _Decimal
    order_date: _date
    ts: _datetime
    gift: bool
    channel: Channel
    coupon: str | None = None
    discount: float | None = None

def test_from_row():
    r = nb.from_row(Row, {"order_id": "O1", "quantity": " 2 ", "price": "9.99", "order_date": "2026-01-05", "ts": "2026-01-05T10:00:00Z",
                          "gift": "yes", "channel": "web", "coupon": "", "discount": "0.1"})
    assert (r.quantity, r.price, r.order_date, r.gift, r.channel, r.coupon, r.discount) == (2, _Decimal("9.99"), _date(2026, 1, 5), True, Channel.WEB, None, 0.1)
    assert r.ts.tzinfo is not None

def test_from_row_errors():
    base = {"order_id": "O1", "quantity": "2", "price": "1", "order_date": "2026-01-05", "ts": "2026-01-05T10:00:00", "gift": "0", "channel": "app"}
    assert nb.from_row(Row, base).coupon is None
    with pytest.raises(TypeError, match="quantity"):
        nb.from_row(Row, {k: v for k, v in base.items() if k != "quantity"})
    with pytest.raises(ValueError):
        nb.from_row(Row, {**base, "quantity": ""})
    with pytest.raises(ValueError):
        nb.from_row(Row, {**base, "channel": "store"})


import dataclasses as _dc
from enum import Enum as _Enum

class Schedule(_Enum):
    HOURLY = "hourly"
    DAILY = "daily"

@_dc.dataclass
class Retry:
    max_attempts: int = 3
    backoff: float = 1.0

@_dc.dataclass
class Job:
    name: str
    source: str
    schedule: Schedule
    retry: Retry = _dc.field(default_factory=Retry)
    tags: list[str] = _dc.field(default_factory=list)
    limits: dict[str, int] = _dc.field(default_factory=dict)
    owner: str | None = None

@_dc.dataclass
class PipelineConfig:
    env: str
    jobs: list[Job]

GOOD = {"env": "dev", "jobs": [{"name": "orders", "source": "s3://raw/orders", "schedule": "daily", "retry": {"max_attempts": 5, "backoff": 2},
                                "tags": ["sales"], "limits": {"rows": 1000}},
                               {"name": "events", "source": "s3://raw/events", "schedule": "hourly", "owner": None}]}

def test_load_typed_ok():
    cfg = nb.load_typed(PipelineConfig, GOOD)
    assert cfg.jobs[0].retry == Retry(5, 2.0) and isinstance(cfg.jobs[0].retry.backoff, float) and cfg.jobs[1].retry == Retry()
    assert cfg.jobs[1].schedule is Schedule.HOURLY and cfg.jobs[0].limits == {"rows": 1000} and cfg.jobs[1].owner is None

@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["jobs"][1]["retry"].update(max_attempts="5") if "retry" in d["jobs"][1] else d["jobs"][1].update(retry={"max_attempts": "5"}), "jobs[1].retry.max_attempts: expected int, got str"),
    (lambda d: d["jobs"][0].update(retries=3), "jobs[0]: unknown keys ['retries']"),
    (lambda d: d["jobs"][0].pop("source"), "jobs[0].source: missing required field"),
    (lambda d: d["jobs"][0].update(schedule="weekly"), "jobs[0].schedule: expected one of"),
    (lambda d: d["jobs"][0]["limits"].update(rows=True), "jobs[0].limits.rows: expected int, got bool"),
    (lambda d: d.update(jobs={}), "jobs: expected list, got dict"),
])
def test_load_typed_errors(mutate, message):
    import copy
    data = copy.deepcopy(GOOD)
    mutate(data)
    with pytest.raises(nb.ConfigError) as info:
        nb.load_typed(PipelineConfig, data)
    assert message in str(info.value) and isinstance(info.value, ValueError)
