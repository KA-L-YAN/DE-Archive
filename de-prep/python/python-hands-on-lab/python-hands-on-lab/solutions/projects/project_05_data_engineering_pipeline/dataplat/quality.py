"""Data-quality checks run on a pipeline's output before it is published.

Each check: func(rows, **params) -> (passed: bool, detail: str). Config: {check, severity: error|warn, ...params}.
"""
from __future__ import annotations

from collections import Counter

from .registry import CHECKS


@CHECKS.register("not_null")
def not_null(rows, column):
    """No None values in column."""
    nulls = sum(1 for r in rows if r.get(column) is None)
    return nulls == 0, f"{nulls} null values in {column}"


@CHECKS.register("unique")
def unique(rows, column):
    """No duplicate non-null values in column."""
    counts = Counter(r.get(column) for r in rows if r.get(column) is not None)
    dupes = {k: v for k, v in counts.items() if v > 1}
    return not dupes, f"{len(dupes)} duplicated values in {column}" + (f" (e.g. {next(iter(dupes))!r})" if dupes else "")


@CHECKS.register("row_count_min")
def row_count_min(rows, value):
    """At least `value` rows."""
    return len(rows) >= value, f"{len(rows)} rows (min {value})"


@CHECKS.register("accepted_values")
def accepted_values(rows, column, values):
    """Every non-null value is in `values`."""
    bad = sorted({str(r.get(column)) for r in rows if r.get(column) is not None and r.get(column) not in values})
    return not bad, f"unexpected values in {column}: {bad[:5]}"


@CHECKS.register("range")
def value_range(rows, column, min=None, max=None):  # noqa: A002 - config keys
    """All non-null values within [min, max]."""
    bad = sum(1 for r in rows if r.get(column) is not None and ((min is not None and r[column] < min) or (max is not None and r[column] > max)))
    return bad == 0, f"{bad} values of {column} outside [{min}, {max}]"


def run_checks(rows: list[dict], checks: list[dict]) -> list[dict]:
    """Run configured checks; returns [{"check", "severity", "passed", "detail"}] (severity defaults to 'error')."""
    results = []
    for cfg in checks:
        params = {k: v for k, v in cfg.items() if k not in ("check", "severity")}
        passed, detail = CHECKS.get(cfg["check"])(rows, **params)
        results.append({"check": cfg["check"], "severity": cfg.get("severity", "error"), "passed": bool(passed), "detail": detail,
                        **({"column": cfg["column"]} if "column" in cfg else {})})
    return results
