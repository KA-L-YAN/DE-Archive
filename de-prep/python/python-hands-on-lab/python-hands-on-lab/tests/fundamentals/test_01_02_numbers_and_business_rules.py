"""Tests for 01_python_fundamentals/02_numbers_and_business_rules.ipynb

Run: pytest tests/fundamentals/test_01_02_numbers_and_business_rules.py -v
"""
import pytest

from labkit.testing import load
from decimal import Decimal

nb = load("01_python_fundamentals/02_numbers_and_business_rules.ipynb")


@pytest.mark.parametrize("amount, pct, expected", [(1999.0, 10, 1799.1), (100, 0, 100.0), (100, 100, 0.0), (0, 50, 0.0), (19.99, 33, 13.39)])
def test_apply_discount(amount, pct, expected):
    assert nb.apply_discount(amount, pct) == expected

@pytest.mark.parametrize("amount, pct", [(100, -1), (100, 100.01), (-5, 10)])
def test_apply_discount_invalid(amount, pct):
    with pytest.raises(ValueError):
        nb.apply_discount(amount, pct)


def test_invoice_totals():
    r = nb.invoice_totals([(2, "999.99"), (1, "0.05")])
    assert r == {"subtotal": Decimal("2000.03"), "tax": Decimal("360.01"), "total": Decimal("2360.04")}

def test_invoice_totals_empty_and_rate():
    assert nb.invoice_totals([])["total"] == Decimal("0.00")
    assert nb.invoice_totals([(1, "100")], tax_rate="0.05")["total"] == Decimal("105.00")

def test_invoice_totals_half_up():
    assert nb.invoice_totals([(1, "0.25")], tax_rate="0.1")["tax"] == Decimal("0.03")

@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "2"])
def test_invoice_totals_bad_qty(qty):
    with pytest.raises(ValueError):
        nb.invoice_totals([(qty, "10.00")])


@pytest.mark.parametrize("w, zone, express, fee", [
    (1, "local", False, 40), (0.2, "local", False, 40), (1.2, "National", False, 105), (2.0, "national", False, 105),
    (3, "local", True, 120), (30, "international", False, 900 + 29 * 300), (1.0001, " LOCAL ", False, 50),
])
def test_shipping_fee(w, zone, express, fee):
    assert nb.shipping_fee(w, zone, express=express) == fee

@pytest.mark.parametrize("w, zone", [(0, "local"), (-1, "local"), (30.01, "local"), (1, "mars")])
def test_shipping_fee_invalid(w, zone):
    with pytest.raises(ValueError):
        nb.shipping_fee(w, zone)


BASE = {"amount": 500, "currency": "INR", "hour": 14, "country": "IN", "home_country": "in"}

@pytest.mark.parametrize("override, expected", [
    ({}, "LOW"), ({"amount": 200001}, "HIGH"), ({"failed_attempts": 3}, "HIGH"), ({"failed_attempts": 2}, "LOW"),
    ({"country": "US", "amount": 50001}, "HIGH"), ({"country": "US", "amount": 50000}, "MEDIUM"),
    ({"hour": 4, "amount": 10001}, "MEDIUM"), ({"hour": 5, "amount": 10001}, "LOW"), ({"hour": 0, "amount": 10000}, "LOW"),
    ({"currency": "usd"}, "MEDIUM"), ({"currency": "inr"}, "LOW"),
])
def test_classify_risk(override, expected):
    assert nb.classify_risk({**BASE, **override}) == expected


@pytest.mark.parametrize("text, expected", [
    ("₹1,23,456.78", "123456.78"), ("$1,234.50", "1234.50"), ("1.234,50 €", "1234.50"), ("(1,200.00)", "-1200.00"),
    ("-45", "-45"), (" 12 ", "12"), ("USD 99.9", "99.9"), ("12,5", "125"), ("12,50", "12.50"), ("1,000,000", "1000000"),
    ("inr 10", "10"),
])
def test_parse_amount(text, expected):
    assert nb.parse_amount(text) == Decimal(expected)

@pytest.mark.parametrize("bad", ["", "   ", "abc", "1e5", "NaN", "12.3.4", "€"])
def test_parse_amount_invalid(bad):
    with pytest.raises(ValueError):
        nb.parse_amount(bad)
