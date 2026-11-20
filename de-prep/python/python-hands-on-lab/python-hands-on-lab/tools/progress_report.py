"""Show how far you are: tests passed / failed / not started, per notebook and project.

    python tools/progress_report.py                 # everything
    python tools/progress_report.py --diagnostic    # diagnostic scores + recommendations only
    python tools/progress_report.py tests/pandas    # one level
    python tools/progress_report.py --solutions     # sanity check: run against the reference solutions

"not started" = tests skipped because the function doesn't exist yet.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POINTS = {1: 1, 2: 2, 3: 2, 4: 3}
DIAG_TARGET = {
    "diagnostic_01": "Level 1 — 01_python_fundamentals",
    "diagnostic_02": "Level 2 — 02_collections",
    "diagnostic_03": "Level 3 — 03_pythonic_python (+ Level 4)",
    "diagnostic_04": "Level 4/5 — 04_java_to_python, 05_functions_and_oop",
    "diagnostic_05": "Level 6/8 — 06_files_json_csv, 08_data_engineering_python",
}


class Collector:
    def __init__(self):
        self.by_file: dict[str, Counter] = defaultdict(Counter)
        self.diag: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            path, _, name = report.nodeid.partition("::")
            self.by_file[path][report.outcome] += 1
            match = re.match(r"test_q(\d)", name)
            if "diagnostic" in path and match:
                self.diag[path][int(match.group(1))].append(report.outcome)


def bar(done: int, total: int, width: int = 20) -> str:
    filled = round(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", default=["tests"])
    parser.add_argument("--diagnostic", action="store_true", help="only run and score the diagnostics")
    parser.add_argument("--solutions", action="store_true", help="run against solutions/ (LAB_TARGET=solutions)")
    args = parser.parse_args(argv)

    import pytest

    os.chdir(ROOT)
    if args.solutions:
        os.environ["LAB_TARGET"] = "solutions"
    paths = ["tests/diagnostic"] if args.diagnostic else args.paths
    collector = Collector()
    with redirect_stdout(io.StringIO()):
        pytest.main([*paths, "-q", "-p", "no:cacheprovider", "--no-header", "-rN"], plugins=[collector])

    if not args.diagnostic:
        print(f"\n{'test file':<62} {'pass':>5} {'fail':>5} {'todo':>5}  progress")
        print("-" * 100)
        totals = Counter()
        for path in sorted(collector.by_file):
            c = collector.by_file[path]
            total = sum(c.values())
            totals.update(c)
            print(f"{path:<62} {c['passed']:>5} {c['failed']:>5} {c['skipped']:>5}  {bar(c['passed'], total)}")
        total = sum(totals.values())
        print("-" * 100)
        print(f"{'TOTAL':<62} {totals['passed']:>5} {totals['failed']:>5} {totals['skipped']:>5}  "
              f"{bar(totals['passed'], total)} {100 * totals['passed'] / total if total else 0:.0f}%")

    if collector.diag:
        print("\nDiagnostic scores (a question scores only if all of its tests pass):\n")
        for path in sorted(collector.diag):
            questions = collector.diag[path]
            earned = sum(POINTS[q] for q, outcomes in questions.items() if outcomes and all(o == "passed" for o in outcomes))
            key = next((k for k in DIAG_TARGET if k in path), path)
            started = any(o != "skipped" for outs in questions.values() for o in outs)
            if not started:
                print(f"  {key:<15} not attempted yet")
                continue
            elif earned <= 4:
                advice = f"do ALL of {DIAG_TARGET.get(key, '')}"
            elif earned <= 6:
                advice = f"do exercises 3-5 of {DIAG_TARGET.get(key, '')}"
            else:
                advice = f"skim {DIAG_TARGET.get(key, '')}, do the Challenges"
            print(f"  {key:<15} {earned}/8 test points   -> {advice} (provisional: add your idiom score, see rubric)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
