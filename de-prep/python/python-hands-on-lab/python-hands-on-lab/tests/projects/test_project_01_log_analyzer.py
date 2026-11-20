"""Tests for Project 1 — Log Analyzer.

Run: pytest tests/projects/test_project_01_log_analyzer.py -v
(LAB_TARGET=solutions runs them against solutions/projects/project_01_log_analyzer)
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from labkit.testing import import_project, project_dir

PROJECT = "project_01_log_analyzer"
parser = import_project(PROJECT, "log_analyzer.parser")
analyzer = import_project(PROJECT, "log_analyzer.analyzer")
report = import_project(PROJECT, "log_analyzer.report")
cli = import_project(PROJECT, "log_analyzer.cli")

ROOT = Path(__file__).resolve().parents[2]
LINE = '2026-03-01T00:00:01.123Z ERROR [payment-service] req=ab12cd34 method=POST path=/api/payments status=500 latency_ms=1203 error=PaymentGatewayTimeout msg="gateway timed out after 1200ms"'
T0 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def rec(minutes=0, level="INFO", service="svc", path="/api/orders/1", status=200, latency=10, error=None):
    return parser.LogRecord(ts=T0 + timedelta(minutes=minutes), level=level, service=service, path=path,
                            status=status, latency_ms=latency, error_type=error)


# ---------------------------------------------------------------- parser
def test_parse_line_full():
    r = parser.parse_line(LINE)
    assert (r.level, r.service, r.request_id, r.method, r.path, r.status, r.latency_ms, r.error_type) == \
        ("ERROR", "payment-service", "ab12cd34", "POST", "/api/payments", 500, 1203, "PaymentGatewayTimeout")
    assert r.message == "gateway timed out after 1200ms" and r.ts.tzinfo is not None and r.traceback is None


@pytest.mark.parametrize("bad", ["", "%%% corrupted line %%%", "2026-03-01T00:00:01.123Z INFO", "2026-03-01 broken [x",
                                 '2026-03-01T00:00:01.123Z NOTICE [svc] req=1', '2026-03-01T00:00:01.123Z INFO [svc] msg="unclosed'])
def test_parse_line_malformed(bad):
    assert parser.parse_line(bad) is None


def test_iter_entries_attaches_tracebacks_only():
    lines = [LINE, "Traceback (most recent call last):", '  File "/app/x.py", line 3, in handle', "    result = process(request)",
             "PaymentGatewayTimeout: gateway timed out", "%%% corrupted line %%%", "", LINE]
    entries = list(parser.iter_entries(lines))
    assert len(entries) == 3 and len(entries[0][1]) == 4 and entries[1] == ("%%% corrupted line %%%", []) and entries[2][1] == []


def test_parse_lines_stats():
    lines = [LINE, "Traceback (most recent call last):", "  File x", "garbage", LINE.replace("ERROR", "INFO")]
    records, stats = parser.parse_lines(lines)
    assert (stats.total_lines, stats.entries, stats.records, stats.malformed, stats.tracebacks) == (5, 3, 2, 1, 1)
    assert records[0].traceback == "Traceback (most recent call last):\n  File x" and stats.malformed_samples == ["garbage"]


def test_parse_real_file():
    records, stats = parser.parse_file(ROOT / "datasets/logs/app.log")
    assert stats.records == 20_000 and 20 < stats.malformed < 200 and stats.tracebacks > 300
    assert stats.total_lines == len((ROOT / "datasets/logs/app.log").read_text(encoding="utf-8", errors="replace").splitlines())


# ---------------------------------------------------------------- analyzer
def test_normalize_path():
    assert analyzer.normalize_path("/api/orders/123") == "/api/orders/{id}" and analyzer.normalize_path("/api/stock/9/items") == "/api/stock/{id}/items"
    assert analyzer.normalize_path("/health") == "/health" and analyzer.normalize_path(None) is None


def test_level_counts_and_top_errors():
    rs = [rec(level="INFO"), rec(level="ERROR", error="DbError"), rec(level="CRITICAL", error="DbError"), rec(level="ERROR", error="Auth"),
          rec(level="WARN", error="Slow"), rec(level="INFO")]
    assert list(analyzer.level_counts(rs).items()) == [("ERROR", 2), ("INFO", 2), ("CRITICAL", 1), ("WARN", 1)]
    assert analyzer.top_error_types(rs) == [("DbError", 2), ("Auth", 1)]


def test_percentile_and_latency():
    assert analyzer.percentile([], 50) is None and analyzer.percentile([1, 2, 3, 4], 50) == 2 and analyzer.percentile(list(range(1, 101)), 95) == 95
    rs = [rec(path=f"/api/orders/{i}", latency=i) for i in range(1, 101)] + [rec(path="/health", latency=None)]
    lat = analyzer.latency_by_endpoint(rs)
    assert lat == {"/api/orders/{id}": {"count": 100, "mean": 50.5, "p50": 50, "p95": 95, "p99": 99}}


def test_error_rate_and_hourly():
    rs = [rec(service="a", status=200), rec(service="a", status=503, level="ERROR"), rec(service="b", status=404), rec(service="b", status=None),
          rec(minutes=61, level="ERROR", service="b", status=500)]
    assert analyzer.error_rate_by_service(rs) == {"a": {"requests": 2, "errors": 1, "error_rate": 0.5}, "b": {"requests": 2, "errors": 1, "error_rate": 0.5}}
    assert analyzer.errors_per_hour(rs) == {"2026-03-01T00:00Z": 1, "2026-03-01T01:00Z": 1}


def test_slowest_requests():
    rs = [rec(minutes=i, latency=l) for i, l in enumerate([5, 900, 900, 30])]
    out = analyzer.slowest_requests(rs, n=2)
    assert [r["latency_ms"] for r in out] == [900, 900] and out[0]["ts"] < out[1]["ts"]


def test_incident_windows():
    burst = [rec(minutes=10 + i * 0.1, level="ERROR", service="pay" if i % 2 else "auth") for i in range(12)]
    later = [rec(minutes=100 + i * 0.1, level="ERROR", service="db") for i in range(10)]
    noise = [rec(minutes=m, level="ERROR") for m in (0, 30, 60)]
    inc = analyzer.incident_windows(burst + later + noise, window_minutes=5, threshold=10)
    assert len(inc) == 2 and inc[0]["errors"] == 12 and inc[0]["services"] == {"auth": 6, "pay": 6} and inc[1]["services"] == {"db": 10}
    assert analyzer.incident_windows(noise, threshold=2) == []


# ---------------------------------------------------------------- report + CLI
def test_build_and_write_report(tmp_path):
    records, stats = parser.parse_lines([LINE, LINE.replace("ERROR", "INFO").replace("status=500", "status=200")])
    rep = report.build_report(records, stats)
    assert rep["summary"]["records"] == 2 and rep["levels"] == {"ERROR": 1, "INFO": 1}
    json.dumps(rep)
    written = report.write_reports(rep, tmp_path / "out", ("json", "md"))
    assert json.loads(written["json"].read_text()) == rep
    md = written["md"].read_text()
    assert md.startswith("# Log analysis report") and "| payment-service | 2 | 1 | 50.00% |" in md
    with pytest.raises(ValueError):
        report.write_reports(rep, tmp_path, ("xml",))


def test_cli_end_to_end(tmp_path):
    code = cli.main(["--input", str(ROOT / "datasets/logs/app.log"), "--output", str(tmp_path / "out"), "--format", "json", "md", "--top", "5"])
    assert code == 0
    rep = json.loads((tmp_path / "out" / "report.json").read_text())
    assert rep["summary"]["records"] == 20_000 and len(rep["top_errors"]) == 5 and rep["incidents"]
    assert cli.main(["--input", str(tmp_path / "missing.log"), "--output", str(tmp_path)]) == 2
