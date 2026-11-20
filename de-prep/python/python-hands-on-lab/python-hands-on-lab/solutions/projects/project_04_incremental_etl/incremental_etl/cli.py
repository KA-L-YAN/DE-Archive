"""CLI with subcommands:

    python main.py run    --input ../../datasets/daily --warehouse warehouse/ --state state/state.json [--full-refresh]
    python main.py status --state state/state.json
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
    p = argparse.ArgumentParser(prog="incremental_etl")
    p.add_argument("--log-level", default="INFO")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="process new/changed input files")
    r.add_argument("--input", required=True, type=Path)
    r.add_argument("--warehouse", required=True, type=Path)
    r.add_argument("--state", required=True, type=Path)
    r.add_argument("--full-refresh", action="store_true", help="wipe warehouse + state and reprocess everything")
    s = sub.add_parser("status", help="show what has been processed")
    s.add_argument("--state", required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    """Dispatch subcommands. Exit codes: 0 ok, 2 bad state/input."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    try:
        if args.command == "run":
            if not args.input.is_dir():
                logging.getLogger("incremental_etl").error("input dir not found: %s", args.input)
                return 2
            result = run(args.input, args.warehouse, args.state, full_refresh=args.full_refresh)
        else:
            result = status(args.state)
    except StateError as exc:
        logging.getLogger("incremental_etl").error("%s", exc)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
