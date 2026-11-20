# Python Hands-On Lab — from Java/Scala developer to Python data engineer

A complete, offline, test-driven practice lab: **59 notebooks with 289 exercises** (20 diagnostic questions + 269 practice exercises, 31 of them flagged as mini-projects),
**5 real-world projects**, realistic messy datasets, a mock REST API, **766 automated tests**, and reference solutions kept in a separate folder.

It's ~80% writing code and ~20% reading. Budget roughly **150–200 hours**: ~100–130 h for the notebooks, ~50–70 h for the projects.

```
Python ─► Pythonic Python ─► Java habits broken ─► Files / APIs ─► Data-engineering Python ─► pandas ─► AWS-style jobs ─► PySpark thinking ─► Capstone platform
```

---

## Who it's for

- You already program professionally (Java, Scala, SQL, Spring Boot, AWS, ETL) and know basic Python syntax.
- Your problem isn't *learning programming* — it's writing Python that *looks and feels like Python*, fluently, without thinking in `ArrayList` and getters.
- You're aiming at data-engineering work (pandas → PySpark → AWS Glue) at the 3–5 YOE level, so the later exercises look like real pipeline work: validation, dedup,
  incremental loads, idempotency, retries, audit trails — not LeetCode.

## Prerequisites

- **Python 3.11 or newer** (3.12/3.13 recommended). The lab uses `tomllib`, `ExceptionGroup`/`except*` and modern typing.
- ~200 MB disk for the virtual environment. No internet needed after installation; **no AWS account or credentials**.
- Optional for one notebook (`12_pyspark_preparation/04_intro_pyspark.ipynb`): Java 17+ and `pyspark`.

## Installation (short version — details in [SETUP.md](SETUP.md))

```bash
cd python-hands-on-lab
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
python -m pip install -r requirements.txt
pytest -q                     # every exercise test shows as "skipped" (not implemented yet) — that's the starting state
jupyter lab                   # open 00_diagnostic/diagnostic_01_core_python.ipynb
```

## How to start

1. Do the five **diagnostics** in `00_diagnostic/` (~30–45 min each, no help). Score them with `python tools/progress_report.py --diagnostic` plus the rubric at the bottom
   of each notebook. The score tells you, per level, whether to do everything, only the harder half, or just the challenges.
2. Work through the levels in order. Record your progress in [PROGRESS.md](PROGRESS.md).
3. Do each project when PROGRESS.md says so (Project 1 after Level 3, ... Project 5 last).

## Folder structure

```
python-hands-on-lab/
├── README.md  SETUP.md  PROGRESS.md  requirements.txt  requirements-spark.txt  pyproject.toml
├── 00_diagnostic/               5 diagnostics (4 questions each) + scoring rubric
├── 01_python_fundamentals/      strings & parsing, numbers & business rules, loops & logs, functions & exceptions
├── 02_collections/              lists, tuples, sets, dicts, nested order data
├── 03_pythonic_python/          comprehensions, enumerate/zip/unpacking, built-ins & key functions, map/filter/functools, generators
├── 04_java_to_python/           ArrayList/HashMap/TreeMap → Python, Streams → comprehensions, beans/Optional/builders, interfaces → duck typing, exceptions
├── 05_functions_and_oop/        *args/**kwargs & signatures, closures, decorators, dunder methods & composition, context managers
├── 06_files_json_csv/           pathlib on a real landing zone, CSV edge cases, JSON/config/env vars, production logging
├── 07_apis/                     requests + mock API, payload processing, 3 pagination styles + watermarks, retries/rate limits/circuit breakers
├── 08_data_engineering_python/  ETL, validation, transformations (windows, SCD2), dedup, incremental processing, idempotent pipelines
├── 09_pandas/                   I/O & dtypes, selection, vectorization, groupby & windows, joins, cleaning pipelines
├── 10_advanced_python/          itertools & lazy pipelines, typing/dataclasses/enums, concurrency (threads, processes, asyncio)
├── 11_python_for_aws/           local S3 (boto3-compatible), Glue-style jobs & bookmarks, CloudWatch EMF, batch processing
├── 12_pyspark_preparation/      map/shuffle/reduce, join strategies & salting, nested data & schemas, DataFrame thinking, intro PySpark
├── 13_real_world_projects/      5 projects: starter code + spec README each
├── datasets/                    generated messy data (CSV, JSON, logs, landing zone, daily partitions, simulated S3) + generator
├── labkit/                      helpers: notebook loader for tests, offline mock API, local HTTP mock server, process-pool workers
├── tests/                       pytest suites, one file per notebook + one per project
├── tools/                       progress_report.py, verify_lab.py
└── solutions/                   reference solutions — same layout as the exercises (delete or hide it any time)
```

## How the notebooks work

Every notebook has the same shape:

- **# Topic → What you'll practice** (a few lines), sometimes a **Setup** cell (sample data / imports — never a solution).
- **Exercise 1 🟢 Easy → Exercise 2 🟢/🟡 → Exercise 3 🟡 Medium → Exercise 4 🟠 Hard → Challenge 🔴 Very Hard** (🧩 = mini-project-sized).
- Each exercise: problem, input, expected output, constraints, an example, the exact **function/class name to implement**, the **pytest command** that checks it,
  and an **empty code cell** for you.

Difficulty increases within each notebook and across levels. Code-quality topics (type hints, docstrings, logging, modules, configuration, testing, packaging) arrive gradually:
none are forced on you in Level 1; by Level 8 they're part of the spec; the projects are full packages with CLIs.

### Running notebooks

`jupyter lab` from the lab root (with the venv active). VS Code / PyCharm notebooks work too — pick the `.venv` interpreter as the kernel.
Notebooks use paths relative to their own folder (`../datasets/...`), so open them from where they are.

## How the tests work

Write your function in the notebook, save, then run its tests from the lab root — the exact command is printed under each exercise:

```bash
pytest tests/fundamentals/test_01_01_strings_and_parsing.py -k normalize_sku -v
pytest tests/fundamentals -v              # a whole level
pytest                                    # everything
python tools/progress_report.py           # per-notebook pass / fail / not-started table
```

The tests **read your notebook**: `labkit/testing.py` executes its code cells (magics stripped, each cell isolated so one broken cell doesn't hide the rest, working
directory = the notebook's folder) and looks up functions by name. A missing function is reported as **skipped — "not implemented yet"**, not as a failure, so `pytest`
always gives an honest picture: green = done, red = wrong, yellow/skipped = not started. Save the notebook before running pytest (the tests read the file on disk).

Tests cover the usual edge cases — empty input, `None`, duplicates, malformed rows, missing fields, wrong types, boundary values, large inputs (100k+ rows) — and many use the real datasets.
API exercises use an injected in-process mock session; time-dependent code receives a fake `sleep`/`clock`, so the whole suite runs in seconds.

## How the solutions are organized

`solutions/` mirrors the exercise folders exactly (`solutions/03_pythonic_python/01_comprehensions.ipynb`, `solutions/projects/project_02_csv_etl/`). For every exercise you get:

1. a working, tested solution (Pythonic by default),
2. an explanation of *why* it's written that way,
3. an alternative where it teaches something — very often the **Java-style version** next to the Pythonic one,
4. time/space complexity,
5. common mistakes.

Run the test suite against the reference solutions with `LAB_TARGET=solutions pytest` (Windows PowerShell: `$env:LAB_TARGET="solutions"; pytest`).
The practice lab is complete without `solutions/` — delete it or move it elsewhere if you don't trust yourself. 🙂

Tip: if you're stuck for more than ~60 minutes, read only the **Explanation** cell of the solution, close it, and retry.

## The projects

| # | Project | Highlights | When |
|---|---|---|---|
| 1 | Log analyzer | multi-line traceback parsing, latency percentiles, sliding-window incident detection, Markdown/JSON reports | after Level 3 |
| 2 | CSV ETL pipeline | header drift + BOMs, row-level rejects with lineage, latest-wins dedup, atomic outputs, audit report, reject-ratio gate | after Level 6 |
| 3 | API ingestion | retries + Retry-After, 3 pagination styles, watermark-based incremental events, state saved last | after Level 7 |
| 4 | Incremental pipeline | content-hash change detection, re-delivery detection, cross-day dedup, per-file checkpoints, crash recovery | after Level 8 |
| 5 | Mini data platform | TOML-declared pipelines, plugin registry, DAG ordering, merge/overwrite sinks, quality gates, dry runs, multi-command CLI | last |

Each starter has the package layout, signatures and docstrings (the spec), a README with requirements and stretch goals, and a test suite (`pytest tests/projects -k project_03`).
Every project runs from the terminal (`python main.py --input ... --output ...`), structured like production code: a package, a thin `cli.py`, pure functions for logic, I/O at the edges.

## Datasets and the mock API

`datasets/` is generated by `datasets/generate_datasets.py` (deterministic, seed 42; rerun it to reset anything you modified). It includes 1k customers, 200 products, 5k+ orders,
10k transactions, 300 employees, 5k events, 1k nested orders, 22k log lines, a landing zone with a corrupt file and a half-written `.tmp`, a week of daily partitions with late
duplicates and a re-delivered file, and a simulated S3 layout. All of it is intentionally messy — see [datasets/README.md](datasets/README.md).

The API exercises run against `labkit.mock_api.MockSession` (in-process, no network) or a real local HTTP server: `python -m labkit.mock_server --port 8765 --fail-rate 0.1`.

## Tracking progress

- [PROGRESS.md](PROGRESS.md): checkboxes for every notebook and project, the recommended order, a table for diagnostic scores, and space for notes.
- `python tools/progress_report.py`: computed progress from the tests.
- `python tools/verify_lab.py`: integrity check of the lab itself (handy if you edit notebooks or regenerate datasets).

## Honest notes

- The solutions are *a* good way, not the only one. If your version passes the tests and reads well, it's fine — compare and keep whichever teaches you more.
- Some challenge tests encode a design decision (e.g. which duplicate wins). If you disagree, change the test — that's a good exercise too.
- The PySpark part is deliberately small. Its job is to make the jump to Spark/Glue feel like a change of API, not a change of mindset.
