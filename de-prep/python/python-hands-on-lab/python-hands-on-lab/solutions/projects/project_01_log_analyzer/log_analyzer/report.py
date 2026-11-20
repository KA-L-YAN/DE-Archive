"""Turn analysis results into a report dict, Markdown, and files on disk."""
from __future__ import annotations

import json
from pathlib import Path

from . import analyzer
from .parser import LogRecord, ParseStats


def build_report(records: list[LogRecord], stats: ParseStats, top: int = 10,
                 window_minutes: int = 5, threshold: int = 10) -> dict:
    """Assemble every metric into one JSON-serializable dict."""
    first, last = analyzer.time_range(records)
    return {
        "summary": {
            "total_lines": stats.total_lines, "entries": stats.entries, "records": stats.records,
            "malformed": stats.malformed, "tracebacks": stats.tracebacks,
            "first_ts": first.isoformat() if first else None, "last_ts": last.isoformat() if last else None,
        },
        "levels": analyzer.level_counts(records),
        "top_errors": [{"error_type": e, "count": c} for e, c in analyzer.top_error_types(records, top)],
        "error_rate_by_service": analyzer.error_rate_by_service(records),
        "latency_by_endpoint": analyzer.latency_by_endpoint(records),
        "errors_per_hour": analyzer.errors_per_hour(records),
        "slowest_requests": analyzer.slowest_requests(records, top),
        "incidents": analyzer.incident_windows(records, window_minutes, threshold),
        "malformed_samples": stats.malformed_samples,
    }


def _table(headers: list[str], rows: list[list]) -> list[str]:
    """Markdown table lines from headers + rows (None -> empty cell)."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in row) + " |" for row in rows]
    return lines


def render_markdown(report: dict) -> str:
    """Render the report as GitHub-flavoured Markdown."""
    s = report["summary"]
    out = ["# Log analysis report", "",
           f"- Lines: **{s['total_lines']}**, entries: **{s['entries']}**, parsed: **{s['records']}**, "
           f"malformed: **{s['malformed']}**, with traceback: **{s['tracebacks']}**",
           f"- Time range: {s['first_ts']} → {s['last_ts']}", "", "## Levels", ""]
    out += _table(["level", "count"], [[k, v] for k, v in report["levels"].items()])
    out += ["", "## Top error types", ""]
    out += _table(["error_type", "count"], [[e["error_type"], e["count"]] for e in report["top_errors"]])
    out += ["", "## Error rate by service (HTTP 5xx)", ""]
    out += _table(["service", "requests", "errors", "error_rate"],
                  [[k, v["requests"], v["errors"], f"{v['error_rate']:.2%}"] for k, v in report["error_rate_by_service"].items()])
    out += ["", "## Latency by endpoint (ms)", ""]
    out += _table(["endpoint", "count", "mean", "p50", "p95", "p99"],
                  [[k, v["count"], v["mean"], v["p50"], v["p95"], v["p99"]] for k, v in report["latency_by_endpoint"].items()])
    out += ["", "## Incidents", ""]
    if report["incidents"]:
        out += _table(["start", "end", "errors", "services"],
                      [[i["start"], i["end"], i["errors"], ", ".join(f"{k}={v}" for k, v in i["services"].items())] for i in report["incidents"]])
    else:
        out.append("No incidents detected.")
    out += ["", "## Slowest requests", ""]
    out += _table(["ts", "service", "path", "latency_ms", "status"],
                  [[r["ts"], r["service"], r["path"], r["latency_ms"], r["status"]] for r in report["slowest_requests"]])
    return "\n".join(out) + "\n"


def write_reports(report: dict, output_dir: str | Path, formats: tuple[str, ...] = ("json", "md")) -> dict[str, Path]:
    """Write report.json / report.md (as requested). Returns {format: path}."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for fmt in formats:
        if fmt == "json":
            path = out / "report.json"
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        elif fmt == "md":
            path = out / "report.md"
            path.write_text(render_markdown(report), encoding="utf-8")
        else:
            raise ValueError(f"unknown format {fmt!r}")
        written[fmt] = path
    return written
