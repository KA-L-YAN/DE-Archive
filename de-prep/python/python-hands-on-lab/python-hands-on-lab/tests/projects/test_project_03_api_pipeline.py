"""Tests for Project 3 — API Ingestion Pipeline.  Run: pytest tests/projects/test_project_03_api_pipeline.py -v"""
import json
from pathlib import Path

import pytest

from labkit.mock_api import BASE_URL, MockSession
from labkit.testing import import_project

PROJECT = "project_03_api_pipeline"
client_mod = import_project(PROJECT, "api_ingest.client")
sources = import_project(PROJECT, "api_ingest.sources")
transform = import_project(PROJECT, "api_ingest.transform")
pipeline = import_project(PROJECT, "api_ingest.pipeline")
cli = import_project(PROJECT, "api_ingest.cli")

ORDER = {"order_id": "O1", "customer_id": "C1", "product_id": "P1", "quantity": 2, "unit_price": 10.25, "status": "shipped",
         "order_ts": "2026-01-05T10:00:00Z", "updated_at": "2026-01-05T12:00:00Z", "channel": "WEB", "country": "IN"}


def client(session, sleeps=None):
    return client_mod.ApiClient(session, BASE_URL, sleep=(sleeps.append if sleeps is not None else (lambda s: None)))


# ---------------------------------------------------------------- client
def test_client_retries_and_metrics():
    sleeps = []
    s = MockSession(data={"customers": [{"customer_id": "C1"}]}, faults={"/customers": [503, "timeout", 429]})
    c = client(s, sleeps)
    assert c.get_json("customers/C1") == {"customer_id": "C1"}
    assert sleeps == [0.5, 1.0, 1.0] and c.metrics == {"requests": 4, "retries": 3, "failures": 0}


def test_client_failures():
    c = client(MockSession(data={"customers": []}, faults={"/customers": [500] * 4}))
    with pytest.raises(client_mod.ApiError) as info:
        c.get_json("customers")
    assert info.value.status == 500 and c.metrics["failures"] == 1 and c.metrics["requests"] == 4
    with pytest.raises(client_mod.ApiError) as info:
        client(MockSession(data={"customers": []})).get_json("customers/none")
    assert info.value.status == 404
    with pytest.raises(client_mod.ApiError) as info:
        client(MockSession(data={"customers": []}, faults={"/customers": ["connection"] * 4})).get_json("customers")
    assert info.value.status is None


# ---------------------------------------------------------------- sources
def test_sources_pagination():
    s = MockSession(data={"customers": [{"customer_id": i} for i in range(237)], "orders": [{"order_id": i} for i in range(250)]})
    c = client(s)
    assert [x["customer_id"] for x in sources.iter_customers(c, page_size=50)] == list(range(237))
    assert len(list(sources.iter_orders(c, limit=100))) == 250
    assert len(list(sources.iter_customers(client(MockSession(data={"customers": []}))))) == 0


def test_fetch_events_incremental():
    evs = [{"event_id": f"e{i}", "updated_at": f"2026-01-01T00:00:{i:02d}Z"} for i in range(30)]
    c = client(MockSession(data={"events": evs}))
    got, wm = sources.fetch_events(c, "2026-01-01T00:00:04Z", limit=10)
    assert len(got) == 25 and wm == "2026-01-01T00:00:29Z"
    assert sources.fetch_events(c, wm) == ([], wm)


# ---------------------------------------------------------------- transform
def test_validate_and_normalize_order():
    assert transform.validate_order(ORDER) == []
    bad = {**ORDER, "quantity": True, "unit_price": None, "status": "lost", "order_ts": "x", "customer_id": ""}
    assert transform.validate_order(bad) == ["customer_id is required", "quantity must be an integer >= 1", "unit_price must be a number >= 0",
                                             "status is invalid", "order_ts is invalid"]
    n = transform.normalize_order(ORDER)
    assert (n["amount"], n["status"], n["channel"], n["order_date"], n["order_ts"]) == (20.5, "SHIPPED", "web", "2026-01-05", "2026-01-05T10:00:00Z")


def test_customers_and_enrich():
    c = {"customer_id": " C1 ", "name": " pavan  kalyan", "email": " PK@X.IO ", "country": "in", "segment": "smb", "is_active": 1}
    assert transform.validate_customer(c) == [] and transform.validate_customer({"name": "", "email": "nope"}) == ["customer_id is required", "name is required", "email is invalid"]
    n = transform.normalize_customer(c)
    assert (n["customer_id"], n["name"], n["email"], n["country"], n["is_active"]) == ("C1", "Pavan Kalyan", "pk@x.io", "IN", True)
    e = transform.enrich_orders([transform.normalize_order(ORDER), transform.normalize_order({**ORDER, "order_id": "O2", "customer_id": "C9"})], {"C1": n})
    assert e[0]["customer_name"] == "Pavan Kalyan" and e[0]["customer_known"] and e[1]["customer_segment"] is None and not e[1]["customer_known"]


def test_latest_by():
    rows = [{"id": 1, "v": "2026-01-02"}, {"id": 1, "v": "2026-01-01"}, {"id": 0, "v": "x"}]
    assert transform.latest_by(rows, "id", "v") == ([{"id": 0, "v": "x"}, {"id": 1, "v": "2026-01-02"}], 1)


# ---------------------------------------------------------------- pipeline + CLI
def test_pipeline_run_against_mock(tmp_path):
    s = MockSession(faults={"/orders": [500, None, "timeout"], "/customers": [429]})
    out, state = tmp_path / "out", tmp_path / "state.json"
    summary = pipeline.run(s, BASE_URL, out, state, page_size=100, sleep=lambda x: None)
    assert summary["customers"]["unique"] == 237 and summary["orders"]["duplicates"] == 15 and summary["orders"]["unique"] == 513
    assert summary["rejects"] == 10 and summary["http"]["retries"] == 3 and summary["events"]["new"] > 300
    assert len((out / "orders.jsonl").read_text().splitlines()) == 513 and json.loads(state.read_text())["events_watermark"] == summary["events"]["watermark"]
    rejects = [json.loads(l) for l in (out / "rejects.jsonl").read_text().splitlines()]
    assert all(r["entity"] == "order" and "unit_price must be a number >= 0" in r["errors"] for r in rejects)
    assert list((out / "events").glob("dt=*/*.jsonl"))
    again = pipeline.run(MockSession(), BASE_URL, out, state, sleep=lambda x: None)
    assert again["events"]["new"] == 0 and again["orders"]["unique"] == 513


def test_pipeline_state_not_saved_on_failure(tmp_path):
    s = MockSession(faults={"/events": [500] * 10})
    with pytest.raises(client_mod.ApiError):
        pipeline.run(s, BASE_URL, tmp_path / "out", tmp_path / "state.json", sleep=lambda x: None)
    assert not (tmp_path / "state.json").exists()


def test_cli(tmp_path, capsys):
    assert cli.main(["--output", str(tmp_path / "o"), "--fail-rate", "0.2", "--log-level", "ERROR"]) == 0
    assert json.loads((tmp_path / "o" / "summary.json").read_text())["orders"]["unique"] == 513
    assert cli.main(["--output", str(tmp_path / "o2"), "--fail-rate", "1.0", "--log-level", "CRITICAL"]) == 1
