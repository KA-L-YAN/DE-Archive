# Real-world projects

| # | Folder | Do it after | Time | Tests |
|---|---|---|---|---|
| 1 | [project_01_log_analyzer](project_01_log_analyzer/README.md) | Level 3 | 5–7 h | `pytest tests/projects -k project_01` |
| 2 | [project_02_csv_etl](project_02_csv_etl/README.md) | Level 6 | 7–10 h | `pytest tests/projects -k project_02` |
| 3 | [project_03_api_pipeline](project_03_api_pipeline/README.md) | Level 7 | 7–9 h | `pytest tests/projects -k project_03` |
| 4 | [project_04_incremental_etl](project_04_incremental_etl/README.md) | Level 8 | 8–12 h | `pytest tests/projects -k project_04` |
| 5 | [project_05_data_engineering_pipeline](project_05_data_engineering_pipeline/README.md) | everything | 20–30 h | `pytest tests/projects -k project_05` |

Each folder is a real Python package with a `main.py` CLI. The starter code contains every module, class and function **signature with its docstring** — the docstrings are the
specification — and bodies that raise `NotImplementedError` (tests for those show as *skipped* until you implement them). Helpers marked `[provided]` are complete.

Run a project's CLI from inside its folder, e.g.:

```bash
cd 13_real_world_projects/project_02_csv_etl
python main.py --input ../../datasets/incoming --output output/
```

Production-structure conventions used throughout: a package of small modules, pure functions for business logic, I/O at the edges, a thin `cli.py` with `argparse` and exit codes,
`logging` instead of `print`, atomic writes, and state committed only after outputs are durable.

Reference implementations: `solutions/projects/`.
