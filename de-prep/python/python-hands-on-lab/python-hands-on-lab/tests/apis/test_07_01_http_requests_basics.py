"""Tests for 07_apis/01_http_requests_basics.ipynb

Run: pytest tests/apis/test_07_01_http_requests_basics.py -v
"""
import pytest

from labkit.testing import load
from labkit.mock_api import MockSession, BASE_URL
import requests

nb = load("07_apis/01_http_requests_basics.ipynb")


def test_get_customer():
    s = MockSession(data={"customers": [{"customer_id": "C1", "name": "Kalyan"}]})
    assert nb.get_customer(s, BASE_URL, "C1") == {"customer_id": "C1", "name": "Kalyan"}
    assert nb.get_customer(s, BASE_URL, "C9") is None

def test_get_customer_server_error():
    s = MockSession(data={"customers": []}, faults={"/customers": [500]})
    with pytest.raises(requests.HTTPError):
        nb.get_customer(s, BASE_URL, "C1")


def test_create_order():
    s = MockSession(data={"customers": []})
    oid = nb.create_order(s, BASE_URL, "C1", [{"product_id": "P1", "qty": 1}])
    assert isinstance(oid, int) and s.calls[-1][0] == "POST"

def test_create_order_validation():
    s = MockSession(data={"customers": []})
    with pytest.raises(ValueError, match="customer_id is required; items must be a non-empty list"):
        nb.create_order(s, BASE_URL, "", [])


def test_build_url():
    assert nb.build_url("https://api.x/v1/", "/orders", status=["NEW", "PAID"], limit=50, cursor=None, active=True) == \
        "https://api.x/v1/orders?status=NEW&status=PAID&limit=50&active=true"
    assert nb.build_url("https://api.x", "customers") == "https://api.x/customers"
    assert nb.build_url("h://a", "s", q="Kalyan B&co") == "h://a/s?q=Kalyan+B%26co"


def test_api_client_auth_and_success():
    s = MockSession(data={"customers": [{"customer_id": "C1"}]}, api_key="secret")
    with pytest.raises(nb.AuthError) as info:
        nb.ApiClient(s, BASE_URL).get_json("/customers/C1")
    assert info.value.status == 401 and isinstance(info.value, nb.ApiError)
    assert nb.ApiClient(s, BASE_URL, api_key="secret").get_json("customers/C1") == {"customer_id": "C1"}

def test_api_client_error_mapping():
    s = MockSession(data={"customers": []}, faults={"/customers": [429, 503, "timeout"]})
    c = nb.ApiClient(s, BASE_URL)
    with pytest.raises(nb.RateLimited) as info:
        c.get_json("customers", page=1)
    assert info.value.retry_after == 1.0
    with pytest.raises(nb.ServerError):
        c.get_json("customers")
    with pytest.raises(requests.Timeout):
        c.get_json("customers")
    with pytest.raises(nb.NotFound):
        c.get_json("customers/nope")
    with pytest.raises(nb.ApiError) as info:
        c.post_json("orders", {})
    assert info.value.status == 422 and info.value.payload["errors"]


def test_fetch_many():
    s = MockSession(data={"customers": [{"customer_id": f"C{i}"} for i in range(50)]}, faults={"/customers/C7": ["timeout"], "/customers/C8": [503]})
    ids = [f"C{i}" for i in range(55)] + ["C1", "C1"]
    found, missing, failed = nb.fetch_many(s, BASE_URL, ids, max_workers=5)
    assert len(found) == 48 and missing == ["C50", "C51", "C52", "C53", "C54"]
    assert set(failed) == {"C7", "C8"} and failed["C7"].startswith("Timeout")
    assert sum(1 for c in s.calls if c[1] == "/customers/C1") == 1
