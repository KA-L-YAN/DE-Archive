"""Built-in sources. Each returns a SourceBatch: records + the file fingerprints that produced them."""
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
    files: dict[str, str] = field(default_factory=dict)   # relative key -> sha256 (for incremental commits)
    malformed: int = 0
    skipped_files: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    """[provided] Chunked SHA-256 of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path, source_key: str) -> list[dict]:
    """All rows of a CSV as dicts (BOM-safe) with `_source` set to source_key."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{**row, "_source": source_key} for row in csv.DictReader(f)]


@SOURCES.register("csv")
def csv_source(cfg, processed: dict[str, str] | None = None) -> SourceBatch:
    """Read one CSV file (cfg.path). Always a full read; `processed` is ignored."""
    return SourceBatch(_read_csv(cfg.path, cfg.path.name), {cfg.path.name: sha256_file(cfg.path)})


@SOURCES.register("csv_partitions")
def csv_partitions_source(cfg, processed: dict[str, str] | None = None) -> SourceBatch:
    """Read `<path>/<partition_key>=*/**.csv`. With `processed` (key -> sha256), files already
    processed with identical content — or whose content equals any processed file (re-delivery) — are skipped.
    Each record gets the partition value under the partition key name.
    """
    processed = processed or {}
    known_hashes = set(processed.values())
    pkey = cfg.options.get("partition_key", "dt")
    batch = SourceBatch(records=[])
    for part_dir in sorted(p for p in cfg.path.glob(f"{pkey}=*") if p.is_dir()):
        value = part_dir.name.split("=", 1)[1]
        for f in sorted(part_dir.glob("*.csv")):
            key = f.relative_to(cfg.path).as_posix()
            digest = sha256_file(f)
            if processed.get(key) == digest or (key not in processed and digest in known_hashes) or digest in batch.files.values():
                batch.skipped_files.append(key)
                continue
            batch.files[key] = digest
            batch.records.extend({**r, pkey: value} for r in _read_csv(f, key))
    return batch


@SOURCES.register("jsonl")
def jsonl_source(cfg, processed: dict[str, str] | None = None) -> SourceBatch:
    """Read JSON Lines; malformed lines and non-objects are counted, not raised. Nested dicts are kept."""
    records, malformed = [], 0
    with cfg.path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(obj, dict):
                records.append({**obj, "_source": cfg.path.name})
            else:
                malformed += 1
    return SourceBatch(records, {cfg.path.name: sha256_file(cfg.path)}, malformed)
