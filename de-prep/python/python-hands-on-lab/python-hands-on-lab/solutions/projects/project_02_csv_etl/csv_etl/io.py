"""File discovery, tolerant CSV reading with lineage, and atomic CSV writing."""
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
    return sorted(p for p in Path(input_dir).glob(pattern)
                  if p.is_file() and not p.name.startswith((".", "_")) and not p.name.endswith((".tmp", ".part")))


def sha256_file(path: str | Path) -> str:
    """[provided] SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_header(name: str) -> str:
    """'  Order ID ' -> 'order_id' (strip, lowercase, spaces/dashes to underscores)."""
    return "_".join(name.strip().lower().replace("-", " ").split())


def read_rows(path: str | Path) -> Iterator[dict]:
    """Yield one dict per data row with normalized header keys plus `_source` and `_line`.

    BOM-safe. Blank lines are skipped. Rows whose field count differs from the header are
    still yielded, with only `_source`, `_line`, `_raw` (the raw list) and `_error` set, so the
    pipeline can reject them with context.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return
        header = [normalize_header(h) for h in header]
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) != len(header):
                yield {"_source": path.name, "_line": reader.line_num, "_raw": row,
                       "_error": f"expected {len(header)} fields, got {len(row)}"}
                continue
            yield {**dict(zip(header, row)), "_source": path.name, "_line": reader.line_num}


def write_csv_atomic(path: str | Path, rows: Iterable[dict], fieldnames: list[str]) -> dict:
    """Write rows to CSV via a temp file + os.replace. Returns {"path", "rows", "sha256"}."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    count = 0
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", restval="")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
                count += 1
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return {"path": str(path), "rows": count, "sha256": sha256_file(path)}


def load_customers(path: str | Path | None) -> dict[str, dict]:
    """customer_id -> customer dict from a JSON array file; {} if path is None or missing."""
    if path is None or not Path(path).is_file():
        return {}
    return {c["customer_id"]: c for c in json.loads(Path(path).read_text(encoding="utf-8"))}
