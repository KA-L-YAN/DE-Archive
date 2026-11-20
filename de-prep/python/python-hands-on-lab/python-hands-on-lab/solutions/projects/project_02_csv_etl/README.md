# Project 2 — CSV ETL Pipeline 🟠

A production-shaped batch ETL over the landing zone `datasets/incoming/`:

```
discover files → read (BOM, header drift, ragged rows) → validate → clean/transform → deduplicate
→ aggregate → write outputs atomically → audit report (+ fail the run if too many rejects)
```

**Estimated time:** 7–10 hours · **Builds on:** Levels 4–6, 8

## What you're given

```
project_02_csv_etl/
├── main.py, config.example.json
└── csv_etl/
    ├── config.py     # Config dataclass + with_overrides (complete); validate(), load_config() TODO
    ├── io.py         # sha256_file (complete); discover_files, normalize_header, read_rows, write_csv_atomic, load_customers TODO
    ├── rules.py      # ValidationError (complete); parse_ts, validate_row, transform, dedupe_latest, daily_summary, customer_summary TODO
    ├── pipeline.py   # RejectThresholdExceeded (complete); run() TODO
    └── cli.py        # build_parser (complete); main() TODO
```

## Requirements

- **Discovery**: `orders_*.csv` by default; skip `.tmp`/`.part`, hidden and `_` files (`_SUCCESS`).
- **Reading**: `orders_03.csv` has a BOM, reordered columns and an extra `coupon_code` column — map by **name**. Ragged rows are yielded with an `_error` so they get rejected *with* file + line.
- **Validation** (first problem wins → `ValidationError(field, message)`): required columns, `quantity` int ≥ 1, `unit_price` ≥ 0, ISO timestamps, `updated_at >= order_ts`, allowed statuses, 2-letter country.
- **Transform**: `amount`, `order_date`, customer segment lookup from `customers.json` (`unknown` if absent).
- **Dedupe**: latest `updated_at` per `order_id` (late corrections arrive in `orders_02.csv`).
- **Outputs** (atomic): `clean_orders.csv`, `daily_summary.csv`, `customer_summary.csv`, `rejected_rows.csv`, `audit.json`.
- **Audit**: per-file stats with input SHA-256, totals, duplicates removed, reject reasons, output row counts + checksums, duration.
- **Gate**: reject ratio above `max_reject_ratio` → write rejects + audit, **don't** publish clean outputs, raise `RejectThresholdExceeded`; CLI exits 1. Bad config → exit 2.

## Run it

```bash
python main.py --input ../../datasets/incoming --output output/
python main.py --input ../../datasets/incoming --output output/ --pattern "*.csv" --max-reject-ratio 0.01   # include corrupt.csv → exit 1
```

## Acceptance criteria

- All tests in `tests/projects/test_project_02_csv_etl.py` pass.
- Re-running produces byte-identical outputs (compare the SHA-256s in two audits).
- No partially written file is ever visible in `output/` (temp file + `os.replace`).

## Stretch goals

- Stream clean rows to disk instead of holding them (dedupe needs an index — keep only `order_id → (updated_at, file offset)`).
- Add `--since YYYY-MM-DD` to process only recent `order_date`s.
- Emit a CloudWatch EMF metrics line (Level 11) at the end of the run.
