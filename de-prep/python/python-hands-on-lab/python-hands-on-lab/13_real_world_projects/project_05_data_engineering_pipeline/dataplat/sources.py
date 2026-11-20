"""Built-in sources. Each returns a SourceBatch: records + the file fingerprints that produced them.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from .registry import SOURCES

@dataclass
class SourceBatch:
    records: list[dict]
    files: dict[str, str] = field(default_factory=dict)
    malformed: int = 0
    skipped_files: list[str] = field(default_factory=list)

def sha256_file(path: Path) -> str:
    """[provided] Chunked SHA-256 of a file."""
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        while (chunk := f.read(1 << 20)):
            digest.update(chunk)
    return digest.hexdigest()

def _read_csv(path: Path, source_key: str) -> list[dict]:
    """All rows of a CSV as dicts (BOM-safe) with `_source` set to source_key."""
    raise NotImplementedError('TODO: implement _read_csv')

@SOURCES.register('csv')
def csv_source(cfg, processed: dict[str, str] | None=None) -> SourceBatch:
    """Read one CSV file (cfg.path). Always a full read; `processed` is ignored."""
    raise NotImplementedError('TODO: implement csv_source')

@SOURCES.register('csv_partitions')
def csv_partitions_source(cfg, processed: dict[str, str] | None=None) -> SourceBatch:
    """Read `<path>/<partition_key>=*/**.csv`. With `processed` (key -> sha256), files already
    processed with identical content — or whose content equals any processed file (re-delivery) — are skipped.
    Each record gets the partition value under the partition key name.
    """
    raise NotImplementedError('TODO: implement csv_partitions_source')

@SOURCES.register('jsonl')
def jsonl_source(cfg, processed: dict[str, str] | None=None) -> SourceBatch:
    """Read JSON Lines; malformed lines and non-objects are counted, not raised. Nested dicts are kept."""
    raise NotImplementedError('TODO: implement jsonl_source')
