# Project 4 — Incremental Data Pipeline 🔴

`datasets/daily/dt=2026-01-01 … dt=2026-01-07/` simulates a week of files landing. Build a pipeline you can run every hour that:

- processes **only new or changed files** (by content hash, not by name),
- **skips re-delivered files** (day 6 contains a renamed copy of a day-5 file),
- **prevents duplicates across days** (day 3 contains late copies of day-2 orders) with a global `order_id → updated_at` index,
- maintains a **current-state orders table** partitioned by `order_date`, rewriting only touched partitions, atomically,
- **quarantines** bad rows per run and source file,
- **checkpoints after every file**, so a crash at file 5 of 13 resumes at file 6 and ends in exactly the same state as a clean run,
- logs one JSON line per processed file.

**Estimated time:** 8–12 hours · **Builds on:** Levels 6, 8 (incremental + idempotent), 11

## What you're given

```
project_04_incremental_etl/
├── main.py
└── incremental_etl/
    ├── state.py        # StateError (complete); PipelineState (TODO)
    ├── processing.py   # InputFile dataclass, sha256_file (complete); discover, classify, validate, parse_file, select_changes (TODO)
    ├── warehouse.py    # Warehouse (TODO)
    ├── pipeline.py     # SimulatedCrash (complete); run, status (TODO)
    └── cli.py          # build_parser (complete); main (TODO)
```

## Run it

```bash
python main.py run --input ../../datasets/daily --warehouse output/warehouse --state output/state.json
python main.py run --input ../../datasets/daily --warehouse output/warehouse --state output/state.json   # processes nothing
python main.py status --state output/state.json
python main.py run --input ../../datasets/daily --warehouse output/warehouse --state output/state.json --full-refresh
```

Simulate days arriving one at a time by copying partitions into an empty `inbox/` and running after each copy.

## Acceptance criteria

- `pytest tests/projects/test_project_04_incremental_etl.py` passes — in particular `test_crash_recovery` and `test_incremental_days_and_idempotency` (day-by-day arrival == one big run).
- A corrupt state file fails loudly (exit code 2) instead of silently reprocessing everything.

## Stretch goals

- Late-data policy: ignore records whose `order_date` is older than N days behind the newest partition (Level 8.5 challenge).
- Retention: delete quarantine folders older than N runs.
- Concurrency guard: a lock file so two runs can't overlap (and stale-lock detection).
