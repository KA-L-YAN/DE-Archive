"""Tests for 08_data_engineering_python/04_deduplication.ipynb

Run: pytest tests/etl/test_08_04_deduplication.py -v
"""
import pytest

from labkit.testing import load

nb = load("08_data_engineering_python/04_deduplication.ipynb")


def test_dedupe_exact():
    rows = [{"a": 1, "b": 2}, {"b": 2, "a": 1}, {"a": 1, "b": 3}, {"a": 1, "b": 2}]
    assert nb.dedupe_exact(rows) == ([{"a": 1, "b": 2}, {"a": 1, "b": 3}], 2) and nb.dedupe_exact([]) == ([], 0)


def test_dedupe_latest():
    rows = [{"id": 2, "v": "a", "ts": 1}, {"id": 1, "v": "b", "ts": 5}, {"id": 2, "v": "c", "ts": 3}, {"id": 1, "v": "d", "ts": 4}, {"id": 2, "v": "e", "ts": 3}]
    assert [(r["id"], r["v"]) for r in nb.dedupe_latest(rows, "id", "ts")] == [(2, "e"), (1, "b")]

def test_dedupe_latest_composite():
    rows = [{"o": 1, "line": 1, "ts": 1, "q": 1}, {"o": 1, "line": 2, "ts": 1, "q": 2}, {"o": 1, "line": 1, "ts": 2, "q": 9}]
    assert [r["q"] for r in nb.dedupe_latest(rows, ("o", "line"), "ts")] == [9, 2]


def test_duplicate_report():
    rows = [{"id": x} for x in ["a", "b", "a", "c", "a", "b", "d"]]
    assert nb.duplicate_report(rows, "id") == {"rows": 7, "distinct_keys": 4, "duplicate_keys": 2, "duplicate_rows": 3, "worst": [("a", 3), ("b", 2)]}

def test_duplicate_report_real():
    import csv
    from pathlib import Path
    with open(Path(__file__).resolve().parents[2] / "datasets/csv/orders.csv", newline="") as f:
        rep = nb.duplicate_report(list(csv.DictReader(f)), "order_id")
    assert rep["distinct_keys"] == 5000 and rep["duplicate_rows"] > 100


def test_normalize_name():
    assert nb.normalize_name("  Jörg  MÜLLER-Smith ") == "jorg muller smith" and nb.normalize_name(None) == ""

def test_fuzzy_duplicates():
    cs = [{"customer_id": "C1", "name": "Pavan Kalyan", "country": "IN"}, {"customer_id": "C2", "name": "pavan kalyan.", "country": "IN"},
          {"customer_id": "C3", "name": "Pavan Kalyann", "country": "IN"}, {"customer_id": "C4", "name": "Pavan Kalyan", "country": "FI"},
          {"customer_id": "C5", "name": "Lukas Müller", "country": "DE"}, {"customer_id": "C6", "name": "Lukas Muller", "country": "DE"}, {"customer_id": "C7", "name": "", "country": "DE"}]
    out = nb.fuzzy_duplicates(cs, threshold=0.9)
    assert out[:2] == [("C1", "C2", 1.0), ("C5", "C6", 1.0)] and ("C1", "C3", 0.96) in out and all(p[0] != "C4" and p[1] != "C4" for p in out)


def test_build_golden_records():
    cs = [{"customer_id": "C3", "name": "PAVAN KALYAN ", "email": "PK@X.IO", "country": "in", "signup_date": "15/03/2024", "is_active": "false", "segment": "retail"},
          {"customer_id": "C1", "name": "Pavan  Kalyan Budamacharla", "email": "pk@x.io ", "country": "IN", "signup_date": "2024-05-01", "is_active": "true", "segment": "smb"},
          {"customer_id": "C2", "name": "", "email": "", "country": "FI", "signup_date": "bad", "is_active": "false", "segment": "enterprise"},
          {"customer_id": "C4", "name": "Diya", "email": "", "country": "IN", "signup_date": "2023-01-01", "is_active": "true", "segment": "retail"}]
    out = nb.build_golden_records(cs)
    assert [g["golden_id"] for g in out] == ["C1", "C2", "C4"]
    g = out[0]
    assert g == {"golden_id": "C1", "source_ids": ["C1", "C3"], "name": "Pavan Kalyan Budamacharla", "email": "pk@x.io", "country": "IN",
                 "signup_date": "2024-03-15", "is_active": True, "segment": "smb"}
    assert out[1]["name"] is None and out[1]["signup_date"] is None and out[1]["email"] is None

def test_build_golden_records_real():
    import csv
    from pathlib import Path
    with open(Path(__file__).resolve().parents[2] / "datasets/csv/customers.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    out = nb.build_golden_records(rows)
    assert len(out) < len(rows) and sum(len(g["source_ids"]) for g in out) == len(rows)
