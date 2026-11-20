# Progress Tracker

Tick boxes as you go (`[ ]` → `[x]`). Get an automatic view any time with `python tools/progress_report.py`.

## Recommended order

1. **00 Diagnostics** → score yourself → note below which levels to do fully, partly, or skim.
2. **Levels 01 → 05** (core Python, collections, Pythonic idioms, Java habits, functions/OOP). Do **Project 1** after Level 3.
3. **Levels 06 → 08** (files, APIs, data engineering). Do **Project 2** after Level 6, **Project 3** after Level 7, **Project 4** after Level 8.
4. **Level 09 pandas**, **10 advanced Python**, **11 AWS-style Python**, **12 PySpark preparation**.
5. **Project 5** (capstone) last.

Within a notebook always go Exercise 1 → Challenge. If an exercise takes more than ~60 minutes, look at the *explanation* (not the code) in the solution notebook, then retry.

## Diagnostic scores

| Diagnostic | Test points (/8) | Idiom score (/2) | Total | Plan for the matching level |
|---|---|---|---|---|
| Diagnostic 1 — Core Python |  |  |  |  |
| Diagnostic 2 — Collections |  |  |  |  |
| Diagnostic 3 — Pythonic Programming |  |  |  |  |
| Diagnostic 4 — Functions & OOP |  |  |  |  |
| Diagnostic 5 — Data Processing |  |  |  |  |

## Diagnostics  ·  `00_diagnostic/`  ·  ~3–4 h

- [ ] **Diagnostic 1 — Core Python** — `diagnostic_01_core_python.ipynb` (4 exercises)
- [ ] **Diagnostic 2 — Collections** — `diagnostic_02_collections.ipynb` (4 exercises)
- [ ] **Diagnostic 3 — Pythonic Programming** — `diagnostic_03_pythonic.ipynb` (4 exercises)
- [ ] **Diagnostic 4 — Functions & OOP** — `diagnostic_04_functions_oop.ipynb` (4 exercises)
- [ ] **Diagnostic 5 — Data Processing** — `diagnostic_05_data_processing.ipynb` (4 exercises)

## Level 1 — Python Fundamentals  ·  `01_python_fundamentals/`  ·  ~6–8 h

- [ ] **Strings & Parsing** — `01_strings_and_parsing.ipynb` (5 exercises)
- [ ] **Numbers, Booleans & Business Rules** — `02_numbers_and_business_rules.ipynb` (5 exercises)
- [ ] **Loops, Control Flow & Log Processing** — `03_loops_and_log_processing.ipynb` (5 exercises)
- [ ] **Functions, Return Values & Exceptions** — `04_functions_and_exceptions.ipynb` (5 exercises)

## Level 2 — Collections  ·  `02_collections/`  ·  ~8–10 h

- [ ] **Lists: Slicing, Sorting, Chunking, Flattening** — `01_lists.ipynb` (5 exercises)
- [ ] **Tuples: Unpacking, Immutable Records, Multiple Returns** — `02_tuples.ipynb` (5 exercises)
- [ ] **Sets: Deduplication, Membership, Set Algebra** — `03_sets.ipynb` (5 exercises)
- [ ] **Dictionaries: Lookup, Aggregation, Merging, Flattening** — `04_dictionaries.ipynb` (5 exercises)
- [ ] **Nested Data: Orders, Items, Customers** — `05_nested_data.ipynb` (5 exercises)

## Level 3 — Pythonic Python  ·  `03_pythonic_python/`  ·  ~8–10 h

- [ ] **Comprehensions: list, dict, set, conditional, nested** — `01_comprehensions.ipynb` (5 exercises)
- [ ] **enumerate, zip, Unpacking & Slicing** — `02_enumerate_zip_unpacking.ipynb` (5 exercises)
- [ ] **any / all / sorted / min / max / sum and Key Functions** — `03_builtins_sorting_keys.ipynb` (5 exercises)
- [ ] **map, filter, lambda, functools & operator** — `04_map_filter_lambda.ipynb` (5 exercises)
- [ ] **Generators & Iterators: Lazy Streaming** — `05_generators_iterators.ipynb` (5 exercises · 🧩 mini-project)

## Level 4 — Break Your Java Habits  ·  `04_java_to_python/`  ·  ~8–10 h

- [ ] **ArrayList / HashMap / HashSet / for-each → Python** — `01_collections_and_iteration.ipynb` (5 exercises)
- [ ] **Java Streams → Comprehensions, Generators & Built-ins** — `02_streams_vs_python.ipynb` (5 exercises)
- [ ] **Beans, Getters/Setters, Optional, Builders, Static Utils → Python** — `03_classes_properties_optional.ipynb` (5 exercises)
- [ ] **Interfaces → Duck Typing, Protocols, ABCs & Dunder Methods** — `04_interfaces_vs_duck_typing.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **try/catch/finally → Python Exception Idioms** — `05_exceptions.ipynb` (5 exercises)

## Level 5 — Functions, OOP & Language Features  ·  `05_functions_and_oop/`  ·  ~9–12 h

- [ ] **Positional, Keyword, Default, *args, **kwargs** — `01_args_kwargs.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **First-Class Functions & Closures** — `02_first_class_functions_closures.ipynb` (5 exercises)
- [ ] **Decorators** — `03_decorators.ipynb` (5 exercises)
- [ ] **Classes: Dunder Methods, Inheritance, Composition, Registries** — `04_classes_inheritance_composition.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Context Managers** — `05_context_managers.ipynb` (5 exercises · 🧩 mini-project)

## Level 6 — Files, CSV, JSON, Config & Logging  ·  `06_files_json_csv/`  ·  ~7–9 h

- [ ] **pathlib & File Handling on a Real Landing Zone** — `01_pathlib_and_files.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **CSV: Encodings, Dialects, Corrupt Rows, Combining Files** — `02_csv_processing.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **JSON, Configuration & Environment Variables** — `03_json_config_env.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Logging Like a Production Service** — `04_logging.ipynb` (5 exercises · 🧩 mini-project)

## Level 7 — APIs  ·  `07_apis/`  ·  ~8–10 h

- [ ] **HTTP with requests: GET, POST, Status Codes, Clients** — `01_http_requests_basics.ipynb` (5 exercises)
- [ ] **Processing API Payloads** — `02_json_api_processing.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Pagination: Page Numbers, Cursors, Links, Watermarks** — `03_pagination.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Retries, Timeouts, Rate Limits & Circuit Breakers** — `04_retries_rate_limits.ipynb` (5 exercises · 🧩 mini-project)

## Level 8 — Data Engineering with Plain Python  ·  `08_data_engineering_python/`  ·  ~14–18 h

- [ ] **ETL Basics: Extract → Transform → Aggregate → Load** — `01_etl_basics.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Data Validation: Required, Types, Rules, References, Schemas** — `02_data_validation.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Transformations: Normalize, Enrich, Derive, Windows, SCD2** — `03_transformations.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Deduplication: Exact, Latest-Wins, Fuzzy, Survivorship** — `04_deduplication.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Incremental Processing: New Files, Checkpoints, Watermarks, Upserts, Late Data** — `05_incremental_processing.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Idempotent Pipelines: Deterministic IDs, Atomic Partitions, Run Ledgers** — `06_idempotent_pipelines.ipynb` (5 exercises · 🧩 mini-project)

## Level 9 — pandas  ·  `09_pandas/`  ·  ~12–15 h

- [ ] **Series, DataFrame, read_csv / read_json, Profiling, Chunks** — `01_dataframe_basics_io.ipynb` (5 exercises)
- [ ] **Selecting, Filtering, Sorting, Top-N, Latest Versions** — `02_filtering_selecting_sorting.ipynb` (5 exercises)
- [ ] **Vectorized Transformations, String Ops, Binning, np.select, Sessionization** — `03_transformations_vectorized.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **groupby, Named Aggregations, Pivots, RFM, Rolling Windows** — `04_groupby_aggregation.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **merge, join, Indicators, Validation, merge_asof, Reconciliation** — `05_joins_merge.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Data Cleaning: Columns, Missing Values, Mixed Dates, Duplicates, Pipelines** — `06_data_cleaning.ipynb` (5 exercises · 🧩 mini-project)

## Level 10 — Advanced Python  ·  `10_advanced_python/`  ·  ~7–9 h

- [ ] **Advanced Iterators: itertools, Windows, Sort-Merge Joins, Lazy Pipelines** — `01_generators_itertools.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Typing, Dataclasses, Enums, singledispatch & Type Introspection** — `02_typing_dataclasses_enums.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Concurrency: Threads, Locks, Processes, asyncio, Producer–Consumer** — `03_concurrency_basics.ipynb` (5 exercises · 🧩 mini-project)

## Level 11 — AWS-Style Python (Simulated Locally)  ·  `11_python_for_aws/`  ·  ~8–10 h

- [ ] **S3 Semantics Locally: URIs, Prefixes, a boto3-like Client, Event-Driven Processing** — `01_s3_simulation.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Glue-Style Jobs: Parameters, Metrics, Bookmarks, a Complete Job** — `02_glue_style_jobs.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Batch Processing: Batching, Backfills, Hash Partitioning, Compaction, Resumable Jobs** — `03_batch_processing.ipynb` (5 exercises · 🧩 mini-project)

## Level 12 — PySpark Preparation  ·  `12_pyspark_preparation/`  ·  ~7–9 h

- [ ] **Map/Shuffle/Reduce, Combiners, Immutable Transformations, Join Strategies, Salting** — `01_functional_partition_thinking.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Nested Data the Spark Way: explode, Structs, Schema Inference, Star Schemas** — `02_nested_data_for_spark.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **DataFrame Thinking: SQL Semantics, NULLs, Partition Pruning, Lazy Plans** — `03_dataframe_thinking.ipynb` (5 exercises · 🧩 mini-project)
- [ ] **Intro to PySpark (optional — needs pyspark + Java)** — `04_intro_pyspark.ipynb` (4 exercises)

## Real-world projects  ·  `13_real_world_projects/`

- [ ] **Project 1 — Log Analyzer** (after Level 3, ~5–7 h) — `13_real_world_projects/project_01_log_analyzer/`
  - [ ] all tests pass: `pytest tests/projects -k project_01`
  - [ ] ran the CLI on the real dataset and read the output
  - [ ] compared design with the reference solution
  - [ ] at least one stretch goal
- [ ] **Project 2 — CSV ETL Pipeline** (after Level 6, ~7–10 h) — `13_real_world_projects/project_02_csv_etl/`
  - [ ] all tests pass: `pytest tests/projects -k project_02`
  - [ ] ran the CLI on the real dataset and read the output
  - [ ] compared design with the reference solution
  - [ ] at least one stretch goal
- [ ] **Project 3 — API Ingestion Pipeline** (after Level 7, ~7–9 h) — `13_real_world_projects/project_03_api_pipeline/`
  - [ ] all tests pass: `pytest tests/projects -k project_03`
  - [ ] ran the CLI on the real dataset and read the output
  - [ ] compared design with the reference solution
  - [ ] at least one stretch goal
- [ ] **Project 4 — Incremental Data Pipeline** (after Level 8, ~8–12 h) — `13_real_world_projects/project_04_incremental_etl/`
  - [ ] all tests pass: `pytest tests/projects -k project_04`
  - [ ] ran the CLI on the real dataset and read the output
  - [ ] compared design with the reference solution
  - [ ] at least one stretch goal
- [ ] **Project 5 — Mini Data Engineering Platform** (last, ~20–30 h) — `13_real_world_projects/project_05_data_engineering_pipeline/`
  - [ ] all tests pass: `pytest tests/projects -k project_05`
  - [ ] ran the CLI on the real dataset and read the output
  - [ ] compared design with the reference solution
  - [ ] at least one stretch goal

## Notes

_Things that surprised me, idioms to remember, questions:_

- 
