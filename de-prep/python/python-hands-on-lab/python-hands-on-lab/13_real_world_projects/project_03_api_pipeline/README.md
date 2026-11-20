# Project 3 — API Ingestion Pipeline 🟠/🔴

Ingest three resources from a flaky REST API (the offline mock in `labkit/mock_api.py`), each with a different pagination style:

| Endpoint | Pagination | Notes |
|---|---|---|
| `/customers` | page number | `total_pages` in the body |
| `/orders` | cursor | duplicates across pages, some `unit_price: null` |
| `/events?since=` | watermark (incremental) | only new events each run |

```
API → resilient client (retries, backoff, Retry-After) → pagination → validation → normalization
    → dedupe → enrichment → JSONL outputs → summary → save watermark (last!)
```

**Estimated time:** 7–9 hours · **Builds on:** Levels 5, 7, 8

## What you're given

```
project_03_api_pipeline/
├── main.py
└── api_ingest/
    ├── client.py      # ApiError (complete); ApiClient (TODO)
    ├── sources.py     # iter_customers, iter_orders, fetch_events (TODO)
    ├── transform.py   # iso() (complete); validate_*, normalize_*, latest_by, enrich_orders (TODO)
    ├── pipeline.py    # write_jsonl_atomic (complete); load_state, save_state, run (TODO)
    └── cli.py         # build_parser, ensure_labkit_importable, make_mock_session (complete); main (TODO)
```

## Requirements

- **Client**: works with *any* requests-like session (duck typing). Retry 408/425/429/5xx, timeouts and connection errors; honour `Retry-After`; exponential backoff otherwise; inject `sleep` for tests; count `requests/retries/failures`. Non-retryable 4xx → `ApiError` immediately.
- **Sources**: generators for customers/orders; `fetch_events` returns `(events, new_watermark)` and never moves the watermark backwards.
- **Transform**: validators return *lists of problems* (records with problems go to `rejects.jsonl` with the reasons); normalized records use UTC ISO timestamps and computed `amount`.
- **Outputs**: `customers.jsonl` and `orders.jsonl` are full snapshots (overwritten → idempotent); new events go to `events/dt=<day>/events-<watermark>.jsonl`; `summary.json`.
- **State**: save the watermark **only after** every output is written. A failed run must leave the old watermark (test: `test_pipeline_state_not_saved_on_failure`).

## Run it

```bash
python main.py --output output/ --fail-rate 0.15          # in-process mock with random transient failures
python main.py --output output/                            # run again: 0 new events
# real HTTP: in another terminal `python -m labkit.mock_server --fail-rate 0.1` (from the lab root), then
python main.py --output output_http/ --base-url http://127.0.0.1:8765/v1
```

## Acceptance criteria

- `pytest tests/projects/test_project_03_api_pipeline.py` passes.
- With `--fail-rate 0.2` the run still succeeds (look at `http.retries` in the summary); with `--fail-rate 1.0` it exits 1 and the watermark file is unchanged.

## Stretch goals

- Fetch customers concurrently by page with a thread pool (Level 10) — keep results ordered.
- Add a token-bucket rate limiter to the client (Level 7, challenge).
- Fix the watermark-tie problem (Level 7.3): use a compound `(updated_at, event_id)` cursor.
