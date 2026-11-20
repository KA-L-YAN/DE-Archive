# Diagnostics

Five short tests of what you already know — **not lessons**. Do them first, without searching or peeking at `solutions/`.

| Notebook | Tests | Time | Feeds into |
|---|---|---|---|
| `diagnostic_01_core_python.ipynb` | strings, numbers, regex, loops, exceptions | 30–40 min | Level 1 |
| `diagnostic_02_collections.ipynb` | dicts, sets, sorting, nested data | 30–40 min | Level 2 |
| `diagnostic_03_pythonic.ipynb` | zip, generators, itertools, built-ins | ~30 min | Levels 3–4 |
| `diagnostic_04_functions_oop.ipynb` | closures, properties, decorators, dunders, context managers | ~40 min | Levels 4–5 |
| `diagnostic_05_data_processing.ipynb` | CSV/JSON, validation, dedup, a mini ETL | ~45 min | Levels 6 and 8 |

**Scoring.** Each notebook has 4 questions worth 1 + 2 + 2 + 3 = 8 *test points* (a question scores only if all its tests pass), plus a self-assessed
*idiom score* of 0–2 after comparing your code with the solution notebook. Total out of 10:

- **0–5** → do the matching level completely
- **6–8** → do exercises 3–5 (Medium → Challenge) of each notebook in that level
- **9–10** → do only the Challenges, then move on

```bash
python tools/progress_report.py --diagnostic
```

Record the totals in `PROGRESS.md`. Re-take a diagnostic after finishing its level — the jump in idiom score is the real signal.
