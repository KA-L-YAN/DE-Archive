"""CLI:  python -m dataplat --config platform.toml <command>

Commands:
  validate-config                         parse + validate, print the execution plan
  plan [--pipeline NAME ...]              show what would run, in order
  run [--pipeline NAME ...] [--dry-run] [--full-refresh] [--run-id ID]
  status                                  tables, row counts, last runs
  show NAME [--limit N]                   print rows of a table as JSON lines

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path
from .config import ConfigError, load_config
from .engine import Engine
EXIT_OK, EXIT_FAILED, EXIT_CONFIG = (0, 1, 2)

def build_parser() -> argparse.ArgumentParser:
    """Argument parser with subcommands (see module docstring)."""
    raise NotImplementedError('TODO: implement build_parser')

def main(argv: list[str] | None=None) -> int:
    """Exit codes: 0 success, 1 run failed / table missing, 2 configuration error."""
    raise NotImplementedError('TODO: implement main')
if __name__ == '__main__':
    sys.exit(main())
