"""Worker functions for process pools.

Functions defined inside a notebook (or any `__main__`) usually can't be sent to worker
processes on Windows/macOS ("spawn" start method), because the child process must
*import* the function by module path. Putting workers in a real module like this one
fixes that — the same reason Spark UDF code must be importable on executors.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_path(path: str) -> tuple[str, str]:
    """Return (path, sha256 hex digest) reading the file in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return str(path), digest.hexdigest()


def count_primes(limit: int) -> int:
    """Deliberately CPU-heavy: count primes below `limit` by trial division."""
    count = 0
    for n in range(2, limit):
        if all(n % d for d in range(2, int(n ** 0.5) + 1)):
            count += 1
    return count


def line_count(path: str) -> tuple[str, int]:
    with open(path, "rb") as f:
        return str(Path(path)), sum(1 for _ in f)
