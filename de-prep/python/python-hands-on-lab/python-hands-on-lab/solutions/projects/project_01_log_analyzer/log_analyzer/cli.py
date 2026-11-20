"""Command-line interface: python main.py --input app.log --output out/"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .parser import parse_file
from .report import build_report, write_reports

log = logging.getLogger("log_analyzer")


def build_parser() -> argparse.ArgumentParser:
    """[provided] Argument parser for the analyzer."""
    p = argparse.ArgumentParser(prog="log_analyzer", description="Analyze application logs and produce a report.")
    p.add_argument("--input", required=True, type=Path, help="log file to analyze")
    p.add_argument("--output", required=True, type=Path, help="directory for report files")
    p.add_argument("--format", nargs="+", default=["json", "md"], choices=["json", "md"])
    p.add_argument("--top", type=int, default=10, help="how many top errors / slow requests to list")
    p.add_argument("--window-minutes", type=int, default=5)
    p.add_argument("--threshold", type=int, default=10, help="errors within the window that open an incident")
    p.add_argument("--log-level", default="INFO")
    return p


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the analysis, write reports. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    if not args.input.is_file():
        log.error("input file not found: %s", args.input)
        return 2
    start = time.perf_counter()
    records, stats = parse_file(args.input)
    log.info("parsed %d records (%d malformed) from %s", stats.records, stats.malformed, args.input)
    report = build_report(records, stats, top=args.top, window_minutes=args.window_minutes, threshold=args.threshold)
    written = write_reports(report, args.output, tuple(args.format))
    log.info("wrote %s in %.2fs", ", ".join(str(p) for p in written.values()), time.perf_counter() - start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
