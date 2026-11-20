# Setup

Everything runs locally and offline after installation. Commands are shown for **macOS/Linux (bash/zsh)** and **Windows (PowerShell)**.

## 1. Install Python 3.11+

Check what you have:

```bash
python3 --version        # macOS/Linux
py --version             # Windows (Python launcher)
```

You need **3.11 or newer** (3.12 or 3.13 recommended).

- **Windows**: install from [https://www.python.org/downloads/](https://www.python.org/downloads/) and tick *"Add python.exe to PATH"*; or `winget install Python.Python.3.12`.
- **macOS**: `brew install python@3.12` (or the python.org installer).
- **Linux (Debian/Ubuntu)**: `sudo apt install python3.12 python3.12-venv` (or use `pyenv`).

## 2. Create and activate a virtual environment

From the `python-hands-on-lab/` folder:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Your prompt should now start with `(.venv)`. Activate it in every new terminal you use for the lab.

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs **pandas**, **numpy**, **requests**, **JupyterLab**, **pytest**, `nbformat`, `ipykernel` and `tzdata` (time-zone data for `zoneinfo` on Windows).
The version ranges are tested with both pandas 2.2 and pandas 3.0.

Verify:

```bash
python -c "import pandas, requests, pytest; print('pandas', pandas.__version__, '| requests', requests.__version__, '| pytest', pytest.__version__)"
```

## 4. Check pytest

```bash
pytest -q
```

Expected on a fresh lab: almost everything **skipped** ("not implemented yet") and nothing failed. To see the suite pass against the reference solutions:

```bash
LAB_TARGET=solutions pytest -q              # macOS/Linux
```

```powershell
$env:LAB_TARGET = "solutions"; pytest -q; Remove-Item Env:LAB_TARGET    # Windows PowerShell
```

## 5. Start Jupyter

```bash
jupyter lab
```

Open `00_diagnostic/diagnostic_01_core_python.ipynb`. If the notebook asks for a kernel, choose *Python 3 (ipykernel)* from the `.venv`.

Using **VS Code**: install the *Python* and *Jupyter* extensions, open the folder, run *Python: Select Interpreter* → `.venv`, then open any `.ipynb`.
Using **PyCharm**: set the project interpreter to `.venv`; notebooks open natively (Professional) or via the Jupyter plugin.

Working loop:

1. Write the function in the empty cell, run the cell, try it on the example.
2. **Save the notebook** (`Ctrl/Cmd + S`) — tests read the file on disk.
3. In a terminal at the lab root: run the `pytest ... -k ...` command shown under the exercise.

## 6. Optional: the local mock API over real HTTP

The API exercises work fully offline with the in-process `MockSession`. To practise with real HTTP calls through `requests`:

```bash
python -m labkit.mock_server --port 8765 --fail-rate 0.1      # leave running in a second terminal
```

then use `requests.Session()` with `base_url = "http://127.0.0.1:8765/v1"` in the notebooks or in Project 3 (`--base-url`).

## 7. Optional: PySpark (only for `12_pyspark_preparation/04_intro_pyspark.ipynb`)

PySpark needs a **Java 17+** runtime:

- macOS: `brew install openjdk@17` (then follow brew's PATH hint)
- Windows: install *Eclipse Temurin 17* ([https://adoptium.net](https://adoptium.net)) and make sure `java -version` works in a new terminal
- Linux: `sudo apt install openjdk-17-jre-headless`

```bash
java -version
python -m pip install -r requirements-spark.txt
pytest tests/pyspark_prep/test_12_04_intro_pyspark.py -v
```

Windows note: local PySpark may warn about `winutils.exe`/`HADOOP_HOME`; reading and writing local CSV/Parquet in the exercises generally works regardless. If it doesn't,
run that one notebook in WSL2 — or skip it. Nothing else in the lab depends on Spark; its tests skip automatically when `pyspark` isn't installed.

## 8. Regenerating datasets

If you modify or delete files under `datasets/`:

```bash
python datasets/generate_datasets.py
```

The generator is deterministic (seed 42), so tests that use the real files keep working.

## Troubleshooting

| Symptom                                                      | Fix                                                                                                                                          |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: labkit` when running pytest          | Run pytest from the lab root (the folder with `pyproject.toml`).                                                                           |
| Tests still "skipped" after writing the function             | Save the notebook; check the function name matches **Implement** exactly.                                                              |
| A test says *some cells raised errors*                     | One of your other cells crashes when executed top to bottom; fix or clear it (*Kernel → Restart & Run All* reproduces what the tests do). |
| `zoneinfo.ZoneInfoNotFoundError` on Windows                | `python -m pip install tzdata` (it's in requirements.txt).                                                                                 |
| `UnicodeDecodeError` reading CSVs on Windows               | Always pass `encoding="utf-8"` (or `"utf-8-sig"`) — the default on Windows is cp1252.                                                   |
| `PicklingError` with `ProcessPoolExecutor` in a notebook | Expected — see Level 10.3: process-pool workers must live in an importable module (`labkit/workers.py`).                                  |
| Jupyter uses the wrong Python                                | `python -m ipykernel install --user --name python-hands-on-lab` and choose that kernel.                                                    |
