"""Tests for 01_python_fundamentals/01_strings_and_parsing.ipynb

Run: pytest tests/fundamentals/test_01_01_strings_and_parsing.py -v
"""
import pytest

from labkit.testing import load

nb = load("01_python_fundamentals/01_strings_and_parsing.ipynb")


@pytest.mark.parametrize("raw, expected", [
    ("  ab_12 cd ", "AB-12-CD"), ("x--y__z", "X-Y-Z"), ("   ", ""), ("", ""),
    ("-lead-trail-", "LEAD-TRAIL"), ("already-OK", "ALREADY-OK"), ("a _ - b", "A-B"),
])
def test_normalize_sku(raw, expected):
    assert nb.normalize_sku(raw) == expected


def test_parse_kv_basic():
    assert nb.parse_kv("user=kalyan; role=admin ;; token=a=b=c") == {"user": "kalyan", "role": "admin", "token": "a=b=c"}

def test_parse_kv_empty_and_trailing():
    assert nb.parse_kv("") == {}
    assert nb.parse_kv("env = prod;") == {"env": "prod"}

def test_parse_kv_duplicates_override():
    assert nb.parse_kv("a=1;a=2") == {"a": "2"}

def test_parse_kv_empty_value_allowed():
    assert nb.parse_kv("a=") == {"a": ""}

@pytest.mark.parametrize("bad", ["oops", "a=1; broken", "=value"])
def test_parse_kv_invalid(bad):
    with pytest.raises(ValueError):
        nb.parse_kv(bad)


@pytest.mark.parametrize("email, expected", [
    ("Pavan.Kalyan@Example.com", "P**********n@example.com"), ("ab@x.io", "a*@x.io"),
    ("a@x.io", "a*@x.io"), ("  abc@X.IO ", "a*c@x.io"),
])
def test_mask_email(email, expected):
    assert nb.mask_email(email) == expected

@pytest.mark.parametrize("bad", ["bad.email", "a@b@c.com", "@x.io", "abc@", ""])
def test_mask_email_invalid(bad):
    with pytest.raises(ValueError):
        nb.mask_email(bad)


LINE = '2026-03-01T00:00:01.123Z ERROR [payment-service] req=ab12cd34 method=POST path=/api/payments status=500 latency_ms=1203 error=PaymentGatewayTimeout msg="gateway timed out after 1200ms"'

def test_parse_log_line_full():
    rec = nb.parse_log_line(LINE)
    assert rec["ts"] == "2026-03-01T00:00:01.123Z" and rec["level"] == "ERROR"
    assert rec["service"] == "payment-service" and rec["path"] == "/api/payments"
    assert rec["status"] == 500 and rec["latency_ms"] == 1203
    assert rec["msg"] == "gateway timed out after 1200ms" and rec["error"] == "PaymentGatewayTimeout"

def test_parse_log_line_info():
    rec = nb.parse_log_line('2026-03-01T00:00:02.000Z INFO [gateway] req=1 method=GET path=/health status=200 latency_ms=3 msg="request completed"')
    assert rec["status"] == 200 and rec["msg"] == "request completed"

@pytest.mark.parametrize("bad", ["", "Traceback (most recent call last):", "%%% corrupted line %%%",
                                 "2026-03-01T00:00:01.123Z INFO", '  File "/app/x.py", line 3, in handle'])
def test_parse_log_line_malformed(bad):
    assert nb.parse_log_line(bad) is None

def test_parse_log_line_real_file():
    from pathlib import Path
    lines = (Path(__file__).resolve().parents[2] / "datasets/logs/app_small.log").read_text().splitlines()
    parsed = [nb.parse_log_line(l) for l in lines]
    good = [p for p in parsed if p]
    assert len(good) > 200 and all(isinstance(p["status"], int) for p in good)


def test_parse_connection_string_full():
    r = nb.parse_connection_string("postgresql://etl_user:p%40ss@db.internal:5432/sales?sslmode=require&connect_timeout=10")
    assert r == {"scheme": "postgresql", "user": "etl_user", "password": "p@ss", "host": "db.internal",
                 "port": 5432, "database": "sales", "params": {"sslmode": "require", "connect_timeout": "10"}}

def test_parse_connection_string_defaults():
    r = nb.parse_connection_string("jdbc:mysql://db/app")
    assert r["port"] == 3306 and r["user"] is None and r["password"] is None and r["params"] == {}
    assert nb.parse_connection_string("redshift://dw.example.com/analytics")["port"] == 5439

@pytest.mark.parametrize("bad", ["postgresql://db.internal:5432/", "oracle://db/x", "postgresql:///sales"])
def test_parse_connection_string_invalid(bad):
    with pytest.raises(ValueError):
        nb.parse_connection_string(bad)
