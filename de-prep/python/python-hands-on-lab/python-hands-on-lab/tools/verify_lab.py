"""Integrity checks for the lab itself (used before packaging; safe to run any time).

    python tools/verify_lab.py

Checks: notebooks are valid nbformat; exercise code cells are empty (except Setup cells); every exercise notebook has a
solution notebook with the same exercises; every required name is defined in the solution; solution code compiles and
executes without errors; every "Check:" command points to an existing test file and selects at least one test;
referenced dataset paths exist; starter projects compile; config files parse.
"""
from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

problems: list[str] = []
counts = {"notebooks": 0, "exercises": 0, "solution_cells": 0}


def fail(msg: str) -> None:
    problems.append(msg)


def cells(nb_path: Path) -> list[dict]:
    import nbformat
    nb = nbformat.read(str(nb_path), as_version=4)
    nbformat.validate(nb)
    return nb.cells


def strip_magics(src: str) -> str:
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("%", "!")))


def defined_names(code_cells: list[str]) -> set[str]:
    names = set()
    for src in code_cells:
        try:
            tree = ast.parse(strip_magics(src))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


HEADER = re.compile(r"^## (Exercise \d+|Challenge|Question \d+) — ", re.M)
IMPLEMENT = re.compile(r"\*\*Implement:\*\* (.+)")
CHECK = re.compile(r'\*\*Check:\*\* `pytest (\S+) -k ("[^"]+"|\S+)`')
DATASET_REF = re.compile(r"datasets/[A-Za-z0-9_./=-]+")


def check_notebooks() -> None:
    from labkit.testing import NotebookNamespace
    import os

    exercise_nbs = sorted(p for p in ROOT.glob("[0-1][0-9]_*/*.ipynb"))
    for nb_path in exercise_nbs:
        rel = nb_path.relative_to(ROOT).as_posix()
        counts["notebooks"] += 1
        try:
            ex_cells = cells(nb_path)
        except Exception as exc:  # invalid JSON / schema
            fail(f"{rel}: invalid notebook ({exc})")
            continue
        md = "\n".join(c.source for c in ex_cells if c.cell_type == "markdown")
        headers = HEADER.findall(md)
        counts["exercises"] += len(headers)
        if len(headers) < 4:
            fail(f"{rel}: only {len(headers)} exercises")
        # exercise code cells must be empty unless directly after a Setup markdown cell
        for i, c in enumerate(ex_cells):
            if c.cell_type == "code" and c.source.strip():
                prev = ex_cells[i - 1] if i else None
                if not (prev is not None and prev.cell_type == "markdown" and prev.source.startswith("### Setup")):
                    fail(f"{rel}: code cell {i} is not empty (possible solution leak)")
        setup_names = defined_names([c.source for c in ex_cells if c.cell_type == "code"])
        required = set()
        for line in IMPLEMENT.findall(md):
            for sig in re.findall(r"`([^`]+)`", line):
                required.add(sig.replace("class ", "").replace("async ", "").split("(")[0].strip())
        leaked = required & setup_names
        if leaked:
            fail(f"{rel}: setup cell defines exercise names {sorted(leaked)}")
        # solution notebook
        sol_path = ROOT / "solutions" / rel
        if not sol_path.exists():
            fail(f"{rel}: missing solution notebook")
            continue
        try:
            sol_cells = cells(sol_path)
        except Exception as exc:
            fail(f"solutions/{rel}: invalid notebook ({exc})")
            continue
        sol_md = "\n".join(c.source for c in sol_cells if c.cell_type == "markdown")
        if HEADER.findall(sol_md) != headers:
            fail(f"{rel}: exercise headers differ from the solution notebook")
        sol_code = [c.source for c in sol_cells if c.cell_type == "code"]
        counts["solution_cells"] += len(sol_code)
        for i, src in enumerate(sol_code):
            try:
                compile(strip_magics(src), f"{sol_path.name}[{i}]", "exec")
            except SyntaxError as exc:
                fail(f"solutions/{rel}: syntax error in code cell {i}: {exc}")
        missing = required - defined_names(sol_code)
        if missing:
            fail(f"solutions/{rel}: does not define {sorted(missing)}")
        # Check: commands
        for test_file, key in CHECK.findall(md):
            tf = ROOT / test_file
            if not tf.exists():
                fail(f"{rel}: Check refers to missing {test_file}")
            else:
                defined = set(re.findall(r"^def (test_\w+)", tf.read_text(), re.M))
                for name in key.strip('"').split(" or "):
                    if name not in defined:
                        fail(f"{rel}: `-k {name}` matches no test in {test_file}")
        # execute the solution notebook (all cells) and the exercise notebook (setup cells) via the test loader
        for path, label in ((sol_path, "solutions/" + rel), (nb_path, rel)):
            needs_spark = "intro_pyspark" in rel
            if needs_spark:
                try:
                    import pyspark  # noqa: F401
                except ImportError:
                    continue
            os.environ["LAB_TARGET"] = "solutions" if path == sol_path else "exercises"
            ns = NotebookNamespace(rel)
            ns._load()
            for idx, err in ns.errors:
                fail(f"{label}: cell {idx} raised {err}")
        os.environ.pop("LAB_TARGET", None)
        for ref in set(DATASET_REF.findall(md + "\n".join(c.source for c in ex_cells if c.cell_type == "code"))):
            target = ROOT / ref.rstrip(".")
            if not target.exists() and not ref.endswith("=") and not any(ch in ref for ch in "*{"):
                fail(f"{rel}: references missing {ref}")


def check_tests_and_projects() -> None:
    for tf in sorted((ROOT / "tests").rglob("test_*.py")):
        text = tf.read_text()
        try:
            compile(text, str(tf), "exec")
        except SyntaxError as exc:
            fail(f"{tf.relative_to(ROOT)}: {exc}")
        for nb in re.findall(r'load\("([^"]+)"\)', text):
            if not (ROOT / nb).exists():
                fail(f"{tf.relative_to(ROOT)}: loads missing notebook {nb}")
        for ref in set(DATASET_REF.findall(text)):
            if not (ROOT / ref.rstrip(".")).exists():
                fail(f"{tf.relative_to(ROOT)}: references missing {ref}")
    for base in (ROOT / "13_real_world_projects", ROOT / "solutions" / "projects"):
        projects = sorted(p for p in base.glob("project_*") if p.is_dir())
        if len(projects) != 5:
            fail(f"{base.relative_to(ROOT)}: expected 5 projects, found {len(projects)}")
        for proj in projects:
            if not (proj / "README.md").exists():
                fail(f"{proj.relative_to(ROOT)}: missing README.md")
            for py in proj.rglob("*.py"):
                try:
                    compile(py.read_text(), str(py), "exec")
                except SyntaxError as exc:
                    fail(f"{py.relative_to(ROOT)}: {exc}")
    for toml_file in [ROOT / "pyproject.toml", *ROOT.glob("**/platform.toml")]:
        try:
            tomllib.loads(toml_file.read_text())
        except tomllib.TOMLDecodeError as exc:
            fail(f"{toml_file.relative_to(ROOT)}: {exc}")
    req = (ROOT / "requirements.txt").read_text()
    for pkg in ("pandas", "requests", "pytest", "jupyterlab", "nbformat"):
        if pkg not in req:
            fail(f"requirements.txt: missing {pkg}")
    for required_file in ["README.md", "SETUP.md", "PROGRESS.md", "datasets/README.md", "datasets/generate_datasets.py",
                          "labkit/testing.py", "labkit/mock_api.py", "labkit/mock_server.py", "tests/conftest.py"]:
        if not (ROOT / required_file).exists():
            fail(f"missing {required_file}")
    for link in re.findall(r"\]\(([^)#]+)\)", (ROOT / "README.md").read_text()):
        if not link.startswith("http") and not (ROOT / link).exists():
            fail(f"README.md: broken link {link}")


def main() -> int:
    check_notebooks()
    check_tests_and_projects()
    print(f"notebooks: {counts['notebooks']}  exercises: {counts['exercises']}  solution code cells: {counts['solution_cells']}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
