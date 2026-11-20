"""File-based tables with overwrite / append / merge write modes and optional partitioning.

Layout:  <root>/<table>/[<partition_by>=<value>/]part-00000.jsonl   (+ <root>/<table>/_meta.json)
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path


class Warehouse:
    def __init__(self, root: str | Path):
        """Remember the warehouse root directory."""
        self.root = Path(root)

    # ---------------- reading
    def exists(self, table: str) -> bool:
        """True if the table has been written at least once."""
        return (self.root / table / "_meta.json").exists()

    def read(self, table: str) -> list[dict]:
        """All rows of a table (partitions in sorted order); unknown table -> KeyError."""
        tdir = self.root / table
        if not self.exists(table):
            raise KeyError(f"table {table!r} does not exist")
        rows = []
        for f in sorted(tdir.rglob("part-*.jsonl")):
            with f.open(encoding="utf-8") as fh:
                rows.extend(json.loads(line) for line in fh if line.strip())
        return rows

    def meta(self, table: str) -> dict:
        """The table's _meta.json ({"rows", "partition_by", "key", "mode", "partitions"})."""
        return json.loads((self.root / table / "_meta.json").read_text(encoding="utf-8"))

    def tables(self) -> list[str]:
        """Names of existing tables."""
        return sorted(p.parent.name for p in self.root.glob("*/_meta.json"))

    # ---------------- writing helpers
    @staticmethod
    def _clean(row: dict) -> dict:
        """Drop lineage keys starting with '_'."""
        return {k: v for k, v in row.items() if not k.startswith("_")}

    @staticmethod
    def _write_rows(path: Path, rows: list[dict], key: str | None) -> None:
        """Atomically write rows as JSONL (sorted by key when given)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(rows, key=lambda r: str(r.get(key))) if key else rows
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in ordered:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
        os.replace(tmp, path)

    def _group(self, rows, partition_by):
        """Group rows by str(partition value) (single None group when unpartitioned)."""
        groups = defaultdict(list)
        for r in rows:
            groups[None if partition_by is None else str(r.get(partition_by))].append(r)
        return groups

    def _write_meta(self, table, mode, partition_by, key):
        """Write <table>/_meta.json with rows, partition_by, key, mode, partitions."""
        tdir = self.root / table
        parts = sorted(p.name.split("=", 1)[1] for p in tdir.glob("*=*") if p.is_dir()) if partition_by else []
        rows = sum(1 for f in tdir.rglob("part-*.jsonl") for line in f.open(encoding="utf-8") if line.strip())
        (tdir / "_meta.json").write_text(json.dumps({"rows": rows, "partition_by": partition_by, "key": key, "mode": mode,
                                                     "partitions": parts}, indent=2), encoding="utf-8")

    # ---------------- write modes
    def write(self, table: str, rows: list[dict], mode: str = "overwrite", partition_by: str | None = None,
              key: str | None = None, version: str | None = None) -> dict:
        """Write rows (lineage columns starting with `_` are dropped). Returns {"rows_written", "partitions"}.

        overwrite: replace the whole table atomically (stage a new directory, then swap)
        append:    add a new part file per partition (part-<n>.jsonl)
        merge:     upsert by `key` (newer `version` wins, ties keep the incoming row); only touched partitions are rewritten
        """
        rows = [self._clean(r) for r in rows]
        tdir = self.root / table
        groups = self._group(rows, partition_by)
        if mode == "overwrite":
            staging = self.root / f".staging-{table}-{uuid.uuid4().hex[:8]}"
            for part, prow in groups.items():
                pdir = staging if part is None else staging / f"{partition_by}={part}"
                self._write_rows(pdir / "part-00000.jsonl", prow, key)
            staging.mkdir(parents=True, exist_ok=True)
            backup = None
            if tdir.exists():
                backup = self.root / f".old-{table}-{uuid.uuid4().hex[:8]}"
                tdir.rename(backup)
            staging.rename(tdir)
            if backup:
                shutil.rmtree(backup)
        elif mode == "append":
            for part, prow in groups.items():
                pdir = tdir if part is None else tdir / f"{partition_by}={part}"
                n = len(list(pdir.glob("part-*.jsonl"))) if pdir.exists() else 0
                self._write_rows(pdir / f"part-{n:05d}.jsonl", prow, None)
        elif mode == "merge":
            if not key:
                raise ValueError("merge needs a key")
            for part, prow in groups.items():
                pdir = tdir if part is None else tdir / f"{partition_by}={part}"
                current = {}
                for f in sorted(pdir.glob("part-*.jsonl")) if pdir.exists() else []:
                    for line in f.open(encoding="utf-8"):
                        if line.strip():
                            r = json.loads(line)
                            current[r[key]] = r
                for r in prow:
                    old = current.get(r[key])
                    if old is None or version is None or (r.get(version) or "") >= (old.get(version) or ""):
                        current[r[key]] = r
                for f in pdir.glob("part-*.jsonl") if pdir.exists() else []:
                    if f.name != "part-00000.jsonl":
                        f.unlink()
                self._write_rows(pdir / "part-00000.jsonl", list(current.values()), key)
        else:
            raise ValueError(f"unknown mode {mode!r}")
        tdir.mkdir(parents=True, exist_ok=True)
        self._write_meta(table, mode, partition_by, key)
        return {"rows_written": len(rows), "partitions": sorted(p for p in groups if p is not None)}
