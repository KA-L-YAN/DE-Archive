"""Statistics over parsed log records. Every function is pure: records in, plain data out."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta
from typing import Iterable

from .parser import LogRecord

ERROR_LEVELS = {"ERROR", "CRITICAL"}
_ID_SEGMENT = re.compile(r"/\d+(?=/|$)")


def normalize_path(path: str | None) -> str | None:
    """Replace numeric path segments with `{id}` so /api/orders/42 and /api/orders/7 group together."""
    if path is None:
        return None
    return _ID_SEGMENT.sub("/{id}", path)


def level_counts(records: Iterable[LogRecord]) -> dict[str, int]:
    """Count records per level, most frequent first (ties alphabetical)."""
    counts = Counter(r.level for r in records)
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def top_error_types(records: Iterable[LogRecord], n: int = 10) -> list[tuple[str, int]]:
    """Most common `error_type` among ERROR/CRITICAL records (ties alphabetical)."""
    counts = Counter(r.error_type for r in records if r.level in ERROR_LEVELS and r.error_type)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def percentile(sorted_values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile of an already sorted list (pct in 0..100)."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def latency_by_endpoint(records: Iterable[LogRecord], percentiles=(50, 95, 99)) -> dict[str, dict]:
    """Per normalized endpoint: count, mean, and nearest-rank percentiles of latency_ms."""
    groups: dict[str, list[int]] = defaultdict(list)
    for r in records:
        if r.path is not None and r.latency_ms is not None:
            groups[normalize_path(r.path)].append(r.latency_ms)
    result = {}
    for endpoint in sorted(groups):
        values = sorted(groups[endpoint])
        stats = {"count": len(values), "mean": round(sum(values) / len(values), 1)}
        stats.update({f"p{p}": percentile(values, p) for p in percentiles})
        result[endpoint] = stats
    return result


def error_rate_by_service(records: Iterable[LogRecord]) -> dict[str, dict]:
    """Per service: requests (records with a status), errors (status >= 500), error_rate (4 dp)."""
    totals, errors = Counter(), Counter()
    for r in records:
        if r.status is None:
            continue
        totals[r.service] += 1
        if r.status >= 500:
            errors[r.service] += 1
    return {svc: {"requests": totals[svc], "errors": errors[svc], "error_rate": round(errors[svc] / totals[svc], 4)}
            for svc in sorted(totals)}


def errors_per_hour(records: Iterable[LogRecord]) -> dict[str, int]:
    """ERROR/CRITICAL count per hour bucket 'YYYY-MM-DDTHH:00Z', chronological."""
    counts = Counter(r.ts.strftime("%Y-%m-%dT%H:00Z") for r in records if r.level in ERROR_LEVELS)
    return dict(sorted(counts.items()))


def slowest_requests(records: Iterable[LogRecord], n: int = 10) -> list[dict]:
    """The n slowest records with latency, as small dicts (ties by timestamp)."""
    with_latency = [r for r in records if r.latency_ms is not None]
    top = sorted(with_latency, key=lambda r: (-r.latency_ms, r.ts))[:n]
    return [{"ts": r.ts.isoformat(), "service": r.service, "path": r.path, "latency_ms": r.latency_ms,
             "status": r.status, "request_id": r.request_id} for r in top]


def incident_windows(records: Iterable[LogRecord], window_minutes: int = 5, threshold: int = 10) -> list[dict]:
    """Detect bursts: periods where ERROR/CRITICAL count within a sliding window reaches `threshold`.

    Consecutive qualifying windows are merged into one incident. Returns
    [{"start", "end", "errors", "services": {service: count}}] (ISO timestamps).
    """
    errors = sorted((r for r in records if r.level in ERROR_LEVELS), key=lambda r: r.ts)
    span = timedelta(minutes=window_minutes)
    window: deque[LogRecord] = deque()
    incidents: list[dict] = []
    current: dict | None = None
    for r in errors:
        window.append(r)
        while window and window[0].ts <= r.ts - span:
            window.popleft()
        if len(window) >= threshold:
            if current is not None and window[0].ts <= current["_end"]:
                current["_end"] = r.ts
                current["_records"].update({id(x): x for x in window})
            else:
                current = {"_start": window[0].ts, "_end": r.ts, "_records": {id(x): x for x in window}}
                incidents.append(current)
    result = []
    for inc in incidents:
        services = Counter(x.service for x in inc["_records"].values())
        result.append({"start": inc["_start"].isoformat(), "end": inc["_end"].isoformat(),
                       "errors": len(inc["_records"]), "services": dict(sorted(services.items()))})
    return result


def time_range(records: list[LogRecord]) -> tuple[datetime | None, datetime | None]:
    """First and last timestamp."""
    if not records:
        return None, None
    return min(r.ts for r in records), max(r.ts for r in records)
