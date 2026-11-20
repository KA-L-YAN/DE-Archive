"""CLI with subcommands:

python main.py run    --input ../../datasets/daily --warehouse warehouse/ --state state/state.json [--full-refresh]
python main.py status --state state/state.json

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path
from .pipeline import run, status
from .state import StateError

def build_parser() -> argparse.ArgumentParser:
    """[provided] argparse with `run` and `status` subcommands."""
    p = argparse.ArgumentParser(prog='incremental_etl')
    p.add_argument('--log-level', default='INFO')
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run', help='process new/changed input files')
    r.add_argument('--input', required=True, type=Path)
    r.add_argument('--warehouse', required=True, type=Path)
    r.add_argument('--state', required=True, type=Path)
    r.add_argument('--full-refresh', action='store_true', help='wipe warehouse + state and reprocess everything')
    s = sub.add_parser('status', help='show what has been processed')
    s.add_argument('--state', required=True, type=Path)
    return p

def main(argv: list[str] | None=None) -> int:
    """Dispatch subcommands. Exit codes: 0 ok, 2 bad state/input."""
    raise NotImplementedError('TODO: implement main')
if __name__ == '__main__':
    sys.exit(main())
