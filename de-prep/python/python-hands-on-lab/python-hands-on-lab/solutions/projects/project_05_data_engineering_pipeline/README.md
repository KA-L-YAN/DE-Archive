# Project 5 — Mini Data Engineering Platform 🔴🔴

The capstone. Instead of one hard-coded pipeline, build a small **platform**: pipelines are declared in `platform.toml`, and an engine
plans, runs, validates and publishes them — the ideas behind dbt, Airflow + Glue jobs, and Delta Live Tables, in ~900 lines of Python.

**Estimated time:** 20–30 hours · **Builds on:** everything

## Architecture

```
platform.toml ──► config.py (load, env overrides, validation, dependency order)
                     │
                     ▼
               engine.py ── plan (topological order, upstream closure)
                     │
       ┌─────────────┼───────────────────────────────────────────┐
       ▼             ▼                     ▼                     ▼
 sources.py     transforms.py          quality.py           warehouse.py
 csv            rename/select/strip     not_null/unique      overwrite (atomic swap)
 csv_partitions upper/lower/title       row_count_min        append
 (incremental)  cast/validate/derive    accepted_values      merge (upsert by key+version,
 jsonl          filter/dedupe/lookup    range                       touched partitions only)
                fill_null/aggregate
       └──── all registered by name via registry.py decorators (plugins) ────┘
                     │
                     ▼
         state/: per-pipeline processed files, runs/<run_id>.json audit
```

## Behaviour to implement (the tests check all of it)

- **Config**: every problem reported at once (`ConfigError.problems`), unknown ops/sources/checks rejected, dependency cycles detected, `{lab_root}` and relative paths resolved, `DATAPLAT_<KEY>` env overrides for `[platform]`.
- **Plan**: dependencies first; `--pipeline X` also runs X's upstream pipelines.
- **Incremental sources**: `csv_partitions` skips files already processed with identical content *and* re-deliveries; state is committed only after a successful publish.
- **Gates**: reject ratio per pipeline (`max_reject_ratio` override) and quality checks with `error`/`warn` severity. A failed pipeline doesn't publish; its downstream pipelines become `UPSTREAM_FAILED`; independent pipelines still run.
- **Idempotency**: rerunning with no new data leaves every table byte-for-byte identical; full-refresh pipelines replace their reject tables instead of accumulating them.
- **Merge sink**: upsert by key with version comparison; only partitions present in the batch are rewritten.
- **Dry run**: transforms and checks run, nothing is written (no tables, no state, no run record).
- **CLI**: `validate-config`, `plan`, `run [--pipeline ...] [--dry-run] [--full-refresh] [--run-id]`, `status`, `show TABLE --limit N`; exit codes 0 / 1 (run failed) / 2 (config).

## What you're given

Only the module layout, the `[provided]` helpers, `platform.toml`, and docstrings. Every other function body is yours. This is intentional: designing the internal
data flow (what a `SourceBatch` holds, what a step returns, where rejects go) is the skill being practised. Read `engine.py`'s docstrings first.

## Run it

```bash
python main.py --config platform.toml validate-config
python main.py --config platform.toml run
python main.py --config platform.toml run                 # fact_orders: SKIPPED_NO_NEW_DATA
python main.py --config platform.toml status
python main.py --config platform.toml show daily_revenue --limit 5
DATAPLAT_MAX_REJECT_RATIO=0.001 python main.py --config platform.toml run    # watch gates + UPSTREAM_FAILED
python -m dataplat --config platform.toml plan --pipeline daily_revenue
```

## Acceptance criteria

- `pytest tests/projects/test_project_05_data_platform.py` passes.
- You can add a new pipeline (e.g. `channel_revenue`) by editing **only** `platform.toml`.
- You can add a new transform (e.g. `explode`) by writing **one** decorated function — no changes to the engine.

## Stretch goals

- A `parquet` sink using `pandas.DataFrame.to_parquet` (add `pyarrow`), and a `pandas` transform that receives/returns a DataFrame.
- Run independent pipelines in parallel (thread pool over the DAG's ready set).
- SCD Type 2 sink mode (Level 8.3 challenge) for `dim_customer`.
- Freshness check: fail if the newest `order_date` is older than N days.
- A Glue-style entry point that reads `--JOB_NAME` / `--config_uri` (Level 11) and runs one pipeline.
