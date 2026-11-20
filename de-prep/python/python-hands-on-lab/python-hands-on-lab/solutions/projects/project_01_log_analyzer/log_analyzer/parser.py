"""Parse application log lines (and attached tracebacks) into LogRecord objects."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

ENTRY_START = re.compile(r"^\d{4}-\d{2}-\d{2}T")
PREFIX = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T[\d:.]+Z) (?P<level>[A-Z]+) \[(?P<service>[\w.-]+)\] (?P<rest>.+)$")
LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class LogRecord:
    ts: datetime
    level: str
    service: str
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    latency_ms: int | None = None
    error_type: str | None = None
    message: str | None = None
    traceback: str | None = None


@dataclass
class ParseStats:
    total_lines: int = 0
    entries: int = 0
    records: int = 0
    malformed: int = 0
    tracebacks: int = 0
    malformed_samples: list[str] = field(default_factory=list)


TRACEBACK_LINE = re.compile(r"^(\s+|Traceback \(most recent call last\):|[A-Za-z_][\w.]*(Error|Exception|Timeout|Declined|Stock|Token|Limited|Unavailable)\b.*:)")


def is_continuation(line: str) -> bool:
    """True for lines that belong to the previous entry: indented lines, the 'Traceback' header,
    and the final 'SomeError: message' line."""
    return bool(TRACEBACK_LINE.match(line))


def iter_entries(lines: Iterable[str]) -> Iterator[tuple[str, list[str]]]:
    """Group raw lines into (entry_line, continuation_lines).

    A line starting with an ISO date begins a new entry. Traceback-shaped lines
    (see `is_continuation`) are attached to the current *valid-looking* entry. Any other
    non-blank line becomes its own entry (it will be counted as malformed). Blank lines
    are ignored.
    """
    current: str | None = None
    extra: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if current is not None and ENTRY_START.match(current) and not ENTRY_START.match(line) and is_continuation(line):
            extra.append(line)
            continue
        if current is not None:
            yield current, extra
        current, extra = line, []
    if current is not None:
        yield current, extra


def parse_line(line: str, continuation: list[str] | None = None) -> LogRecord | None:
    """Parse one entry line; attach continuation lines as `traceback`. Return None if malformed."""
    match = PREFIX.match(line.strip())
    if not match or match["level"] not in LEVELS:
        return None
    try:
        ts = datetime.fromisoformat(match["ts"].replace("Z", "+00:00"))
        tokens = shlex.split(match["rest"])
    except ValueError:
        return None
    fields: dict[str, str] = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if not sep:
            return None
        fields[key] = value

    def as_int(name: str) -> int | None:
        value = fields.get(name)
        return int(value) if value is not None and value.isdigit() else None

    return LogRecord(
        ts=ts, level=match["level"], service=match["service"], request_id=fields.get("req"),
        method=fields.get("method"), path=fields.get("path"), status=as_int("status"),
        latency_ms=as_int("latency_ms"), error_type=fields.get("error"), message=fields.get("msg"),
        traceback="\n".join(continuation) if continuation else None,
    )


def parse_lines(lines: Iterable[str]) -> tuple[list[LogRecord], ParseStats]:
    """Parse an iterable of raw lines into records plus statistics."""
    stats = ParseStats()

    def counted(source):
        for line in source:
            stats.total_lines += 1
            yield line

    records = []
    for entry, extra in iter_entries(counted(lines)):
        stats.entries += 1
        record = parse_line(entry, extra)
        if record is None:
            stats.malformed += 1
            if len(stats.malformed_samples) < 5:
                stats.malformed_samples.append(entry[:120])
            continue
        if record.traceback:
            stats.tracebacks += 1
        records.append(record)
    stats.records = len(records)
    return records, stats


def parse_file(path: str | Path) -> tuple[list[LogRecord], ParseStats]:
    """Parse a log file (UTF-8, undecodable bytes replaced)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_lines(f)
