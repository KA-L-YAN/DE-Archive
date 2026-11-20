"""File discovery, tolerant CSV reading with lineage, and atomic CSV writing.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

def discover_files(input_dir: str | Path, pattern: str) -> list[Path]:
    """Sorted data files matching `pattern`; skip hidden/underscore files, *.tmp / *.part, and directories."""
    raise NotImplementedError('TODO: implement discover_files')

def sha256_file(path: str | Path) -> str:
    """[provided] SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        while (chunk := f.read(1 << 20)):
            digest.update(chunk)
    return digest.hexdigest()

def normalize_header(name: str) -> str:
    """'  Order ID ' -> 'order_id' (strip, lowercase, spaces/dashes to underscores)."""
    raise NotImplementedError('TODO: implement normalize_header')

def read_rows(path: str | Path) -> Iterator[dict]:
    """Yield one dict per data row with normalized header keys plus `_source` and `_line`.

    BOM-safe. Blank lines are skipped. Rows whose field count differs from the header are
    still yielded, with only `_source`, `_line`, `_raw` (the raw list) and `_error` set, so the
    pipeline can reject them with context.
    """
    raise NotImplementedError('TODO: implement read_rows')

def write_csv_atomic(path: str | Path, rows: Iterable[dict], fieldnames: list[str]) -> dict:
    """Write rows to CSV via a temp file + os.replace. Returns {"path", "rows", "sha256"}."""
    raise NotImplementedError('TODO: implement write_csv_atomic')

def load_customers(path: str | Path | None) -> dict[str, dict]:
    """customer_id -> customer dict from a JSON array file; {} if path is None or missing."""
    raise NotImplementedError('TODO: implement load_customers')
