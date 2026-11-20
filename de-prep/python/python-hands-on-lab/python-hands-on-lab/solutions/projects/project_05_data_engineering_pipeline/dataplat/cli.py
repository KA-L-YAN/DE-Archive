"""CLI:  python -m dataplat --config platform.toml <command>

Commands:
  validate-config                         parse + validate, print the execution plan
  plan [--pipeline NAME ...]              show what would run, in order
  run [--pipeline NAME ...] [--dry-run] [--full-refresh] [--run-id ID]
  status                                  tables, row counts, last runs
  show NAME [--limit N]                   print rows of a table as JSON lines
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .engine import Engine

EXIT_OK, EXIT_FAILED, EXIT_CONFIG = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    """Argument parser with subcommands (see module docstring)."""
    p = argparse.ArgumentParser(prog="dataplat", description="Mini data platform: declarative, incremental, idempotent pipelines.")
    p.add_argument("--config", type=Path, default=Path("platform.toml"))
    p.add_argument("--log-level", default=None, help="overrides [platform] log_level")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-config")
    plan = sub.add_parser("plan")
    plan.add_argument("--pipeline", action="append")
    run = sub.add_parser("run")
    run.add_argument("--pipeline", action="append")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--full-refresh", action="store_true")
    run.add_argument("--run-id")
    sub.add_parser("status")
    show = sub.add_parser("show")
    show.add_argument("table")
    show.add_argument("--limit", type=int, default=5)
    return p


def main(argv: list[str] | None = None) -> int:
    """Exit codes: 0 success, 1 run failed / table missing, 2 configuration error."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG
    logging.basicConfig(level=(args.log_level or config.log_level).upper(), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    engine = Engine(config)
    if args.command == "validate-config":
        print(f"OK: {len(config.sources)} sources, {len(config.pipelines)} pipelines; plan: {' -> '.join(engine.plan())}")
        return EXIT_OK
    if args.command == "plan":
        try:
            print("\n".join(engine.plan(args.pipeline)))
        except KeyError as exc:
            print(exc, file=sys.stderr)
            return EXIT_CONFIG
        return EXIT_OK
    if args.command == "run":
        report = engine.run(args.pipeline, dry_run=args.dry_run, full_refresh=args.full_refresh, run_id=args.run_id)
        print(json.dumps(report.to_dict(), indent=2, default=str))
        return EXIT_OK if report.status == "SUCCEEDED" else EXIT_FAILED
    if args.command == "status":
        tables = {t: engine.warehouse.meta(t)["rows"] for t in engine.warehouse.tables()}
        runs = [{"run_id": r["run_id"], "status": r["status"]} for r in engine.state.runs()[-5:]]
        print(json.dumps({"tables": tables, "recent_runs": runs}, indent=2))
        return EXIT_OK
    if args.command == "show":
        try:
            rows = engine.warehouse.read(args.table)
        except KeyError as exc:
            print(exc, file=sys.stderr)
            return EXIT_FAILED
        for r in rows[: args.limit]:
            print(json.dumps(r, ensure_ascii=False))
        return EXIT_OK
    return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
