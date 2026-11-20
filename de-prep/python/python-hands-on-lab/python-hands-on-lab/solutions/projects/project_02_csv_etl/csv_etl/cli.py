"""CLI: python main.py --input ../../datasets/incoming --output output/ [--config config.json]"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .pipeline import RejectThresholdExceeded, run

EXIT_OK, EXIT_REJECTS, EXIT_CONFIG = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    """[provided] CLI arguments; anything not given falls back to the config file, then defaults."""
    p = argparse.ArgumentParser(prog="csv_etl", description="Validate, deduplicate and aggregate order CSVs.")
    p.add_argument("--input", dest="input_dir", type=Path)
    p.add_argument("--output", dest="output_dir", type=Path)
    p.add_argument("--config", type=Path, help="optional JSON config file")
    p.add_argument("--pattern")
    p.add_argument("--max-reject-ratio", type=float)
    p.add_argument("--run-id")
    p.add_argument("--log-level", default="INFO")
    return p


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline. Exit codes: 0 success, 1 reject threshold exceeded, 2 configuration/input error."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    try:
        config = load_config(args.config, input_dir=args.input_dir, output_dir=args.output_dir,
                             pattern=args.pattern, max_reject_ratio=args.max_reject_ratio)
    except ConfigError as exc:
        logging.getLogger("csv_etl").error("configuration error: %s", exc)
        return EXIT_CONFIG
    try:
        audit = run(config, run_id=args.run_id)
    except RejectThresholdExceeded as exc:
        logging.getLogger("csv_etl").error("%s (see %s/audit.json)", exc, config.output_dir)
        return EXIT_REJECTS
    print(f"OK run_id={audit['run_id']} unique_orders={audit['totals']['unique_orders']} rejected={audit['totals']['rejected']}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
