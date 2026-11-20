# Project 1 — Log Analyzer 🟠

Turn 22,000 lines of messy application logs (`datasets/logs/app.log`) into an incident report an on-call engineer would actually use.

**Estimated time:** 5–7 hours · **Builds on:** Levels 1–3, 6 (strings, regex, collections, generators, files, logging)

## What you're given

```
project_01_log_analyzer/
├── main.py                  # entry point (complete)
└── log_analyzer/
    ├── parser.py            # LogRecord + ParseStats dataclasses (complete); parsing functions (TODO)
    ├── analyzer.py          # statistics (TODO)
    ├── report.py            # report dict, Markdown rendering, writing files (TODO)
    └── cli.py               # build_parser() complete; main() TODO
```

Every TODO function has its signature and a docstring that **is the specification**. The tests in
`tests/projects/test_project_01_log_analyzer.py` check it.

## The input

```
2026-03-01T00:00:01.123Z ERROR [payment-service] req=ab12cd34 method=POST path=/api/payments status=500 latency_ms=1203 error=PaymentGatewayTimeout msg="gateway timed out after 1200ms"
Traceback (most recent call last):
  File "/app/payment/handlers.py", line 88, in handle
    result = process(request)
PaymentGatewayTimeout: gateway timed out after 1200ms
%%% corrupted line %%%
```

## Requirements

1. **Parsing** (`parser.py`)
   - `iter_entries` groups lines: a timestamped line starts an entry; traceback-shaped lines (indented, `Traceback ...`, `SomeError: msg`) attach to it; any other line is its own (malformed) entry.
   - `parse_line` → `LogRecord` or `None`. `msg` may contain spaces (quoted). Ints for `status` / `latency_ms`.
   - `parse_lines` / `parse_file` return records **and** `ParseStats` (lines, entries, records, malformed, tracebacks, up to 5 malformed samples). Stream the file.
2. **Analysis** (`analyzer.py`) — pure functions: level counts, top error types, per-endpoint latency percentiles (normalize `/api/orders/123` → `/api/orders/{id}`), 5xx error rate per service, errors per hour, slowest requests, **incident detection** (sliding window: ≥ N errors within W minutes; overlapping windows merge into one incident).
3. **Reporting** (`report.py`) — one JSON-serializable dict, a readable Markdown report with tables, `write_reports` for `json` and/or `md`.
4. **CLI** — `python main.py --input ../../datasets/logs/app.log --output output/ --format json md --top 10 --window-minutes 5 --threshold 10`. Exit code 2 when the input is missing. Log progress with `logging`, not `print`.

## Acceptance criteria

- `pytest tests/projects/test_project_01_log_analyzer.py` passes (run from the lab root).
- Parses `app.log` in well under 2 seconds; memory stays flat (iterate the file, don't `read()` it).
- `report.md` opens nicely in VS Code's Markdown preview.

## Stretch goals

- `--since/--until` time filters; `--service` filter.
- Detect the *start* of an incident per service and report the top error type in each incident.
- Parse `datasets/logs/access.log` (Apache combined format) with a second parser and the same analyzer.
- Package it: add a `[project.scripts]` entry so `log-analyzer --input ...` works after `pip install -e .`.

Reference solution: `solutions/projects/project_01_log_analyzer/` (don't peek until you've passed most tests).
