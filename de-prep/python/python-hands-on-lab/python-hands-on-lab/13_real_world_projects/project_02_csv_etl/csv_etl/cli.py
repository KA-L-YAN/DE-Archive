"""CLI: python main.py --input ../../datasets/incoming --output output/ [--config config.json]

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from .config import ConfigError, load_config
from .pipeline import RejectThresholdExceeded, run
EXIT_OK, EXIT_REJECTS, EXIT_CONFIG = (0, 1, 2)

def build_parser() -> argparse.ArgumentParser:
    """[provided] CLI arguments; anything not given falls back to the config file, then defaults."""
    p = argparse.ArgumentParser(prog='csv_etl', description='Validate, deduplicate and aggregate order CSVs.')
    p.add_argument('--input', dest='input_dir', type=Path)
    p.add_argument('--output', dest='output_dir', type=Path)
    p.add_argument('--config', type=Path, help='optional JSON config file')
    p.add_argument('--pattern')
    p.add_argument('--max-reject-ratio', type=float)
    p.add_argument('--run-id')
    p.add_argument('--log-level', default='INFO')
    return p

def main(argv: list[str] | None=None) -> int:
    """Run the pipeline. Exit codes: 0 success, 1 reject threshold exceeded, 2 configuration/input error."""
    raise NotImplementedError('TODO: implement main')
if __name__ == '__main__':
    sys.exit(main())
