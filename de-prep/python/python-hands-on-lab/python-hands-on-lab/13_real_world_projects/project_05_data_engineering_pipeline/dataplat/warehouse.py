"""File-based tables with overwrite / append / merge write modes and optional partitioning.

Layout:  <root>/<table>/[<partition_by>=<value>/]part-00000.jsonl   (+ <root>/<table>/_meta.json)

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
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
        raise NotImplementedError('TODO: implement __init__')

    def exists(self, table: str) -> bool:
        """True if the table has been written at least once."""
        raise NotImplementedError('TODO: implement exists')

    def read(self, table: str) -> list[dict]:
        """All rows of a table (partitions in sorted order); unknown table -> KeyError."""
        raise NotImplementedError('TODO: implement read')

    def meta(self, table: str) -> dict:
        """The table's _meta.json ({"rows", "partition_by", "key", "mode", "partitions"})."""
        raise NotImplementedError('TODO: implement meta')

    def tables(self) -> list[str]:
        """Names of existing tables."""
        raise NotImplementedError('TODO: implement tables')

    @staticmethod
    def _clean(row: dict) -> dict:
        """Drop lineage keys starting with '_'."""
        raise NotImplementedError('TODO: implement _clean')

    @staticmethod
    def _write_rows(path: Path, rows: list[dict], key: str | None) -> None:
        """Atomically write rows as JSONL (sorted by key when given)."""
        raise NotImplementedError('TODO: implement _write_rows')

    def _group(self, rows, partition_by):
        """Group rows by str(partition value) (single None group when unpartitioned)."""
        raise NotImplementedError('TODO: implement _group')

    def _write_meta(self, table, mode, partition_by, key):
        """Write <table>/_meta.json with rows, partition_by, key, mode, partitions."""
        raise NotImplementedError('TODO: implement _write_meta')

    def write(self, table: str, rows: list[dict], mode: str='overwrite', partition_by: str | None=None, key: str | None=None, version: str | None=None) -> dict:
        """Write rows (lineage columns starting with `_` are dropped). Returns {"rows_written", "partitions"}.

        overwrite: replace the whole table atomically (stage a new directory, then swap)
        append:    add a new part file per partition (part-<n>.jsonl)
        merge:     upsert by `key` (newer `version` wins, ties keep the incoming row); only touched partitions are rewritten
        """
        raise NotImplementedError('TODO: implement write')
