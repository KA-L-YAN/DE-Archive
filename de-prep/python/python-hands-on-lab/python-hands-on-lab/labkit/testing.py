"""Load functions you wrote inside a Jupyter notebook so pytest can test them.

How it works
------------
``load("01_python_fundamentals/01_strings_and_parsing.ipynb")`` returns a lazy
namespace. The first time a test touches an attribute (``nb.normalize_sku``),
every code cell of that notebook is executed into a fresh module:

* IPython magics / shell lines (``%timeit``, ``!pip``) are stripped.
* Each cell runs independently: a cell that raises does not stop the others.
* stdout/stderr are silenced and the working directory is the notebook's folder,
  so relative paths like ``../datasets/csv/orders.csv`` behave like in Jupyter.

If a name is missing, ``NotImplementedError`` is raised and the test is reported
as *skipped* ("not implemented yet") rather than failed. Once you define the
function, the test starts passing or failing for real.

Set ``LAB_TARGET=solutions`` to run the same tests against ``solutions/``.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def target() -> str:
    return os.environ.get("LAB_TARGET", "exercises").strip().lower()


def notebook_path(rel: str) -> Path:
    base = ROOT / "solutions" if target() == "solutions" else ROOT
    return base / rel


def _clean(source: str) -> str:
    lines = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("%", "!")):
            continue
        lines.append(line)
    return "\n".join(lines)


_CACHE: dict[str, "NotebookNamespace"] = {}


class NotebookNamespace:
    def __init__(self, rel: str):
        self._rel = rel
        self._module: types.ModuleType | None = None
        self.errors: list[tuple[int, str]] = []

    def _load(self) -> types.ModuleType:
        if self._module is not None:
            return self._module
        path = notebook_path(self._rel)
        if not path.exists():
            raise NotImplementedError(f"Notebook not found: {path}")
        nb = json.loads(path.read_text(encoding="utf-8"))
        name = "labnb_" + hashlib.md5(str(path).encode()).hexdigest()[:10]
        module = types.ModuleType(name)
        module.__file__ = str(path)
        sys.modules[name] = module
        old_cwd = os.getcwd()
        os.chdir(path.parent)
        try:
            for idx, cell in enumerate(nb.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue
                src = cell.get("source", "")
                src = "".join(src) if isinstance(src, list) else src
                src = _clean(src)
                if not src.strip():
                    continue
                try:
                    code = compile(src, f"{path.name}[cell {idx}]", "exec")
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        exec(code, module.__dict__)
                except Exception as exc:  # keep going: one broken cell must not hide the rest
                    self.errors.append((idx, f"{type(exc).__name__}: {exc}"))
        finally:
            os.chdir(old_cwd)
        self._module = module
        return module

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        module = self._load()
        try:
            return module.__dict__[name]
        except KeyError:
            hint = ""
            if self.errors:
                hint = " (note: some cells raised errors: " + "; ".join(e for _, e in self.errors[:3]) + ")"
            raise NotImplementedError(f"`{name}` is not defined in {self._rel}{hint}") from None


def load(rel: str) -> NotebookNamespace:
    """Return a lazy namespace for the notebook at ``rel`` (relative to the lab root)."""
    key = f"{target()}::{rel}"
    if key not in _CACHE:
        _CACHE[key] = NotebookNamespace(rel)
    return _CACHE[key]


def project_dir(name: str) -> Path:
    """Directory of a real-world project (starter or solution, depending on LAB_TARGET)."""
    if target() == "solutions":
        return ROOT / "solutions" / "projects" / name
    return ROOT / "13_real_world_projects" / name


def import_project(name: str, package: str):
    """Import a project's package from the starter or solution directory."""
    import importlib

    path = str(project_dir(name))
    if path not in sys.path:
        sys.path.insert(0, path)
    for mod in list(sys.modules):
        if mod == package or mod.startswith(package + "."):
            mod_file = getattr(sys.modules[mod], "__file__", "") or ""
            if not mod_file.startswith(path):
                del sys.modules[mod]
    return importlib.import_module(package)
