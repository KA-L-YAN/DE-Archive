"""CLI: python main.py --output output/ [--fail-rate 0.1] [--base-url http://127.0.0.1:8765/v1]"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

from .client import ApiError
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    """[provided] CLI arguments."""
    p = argparse.ArgumentParser(prog="api_ingest", description="Ingest customers, orders and events from the (mock) API.")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--state", type=Path, help="state file (default: <output>/_state.json)")
    p.add_argument("--base-url", help="real HTTP endpoint, e.g. http://127.0.0.1:8765/v1 (python -m labkit.mock_server)")
    p.add_argument("--fail-rate", type=float, default=0.0, help="in-process mock only: fraction of calls that fail transiently")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--log-level", default="INFO")
    return p


def ensure_labkit_importable() -> None:
    """[provided] Put the lab root (the folder containing `labkit/`) on sys.path."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "labkit").is_dir():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return


def make_mock_session(fail_rate: float, seed: int):
    """[provided] In-process MockSession with deterministic random transient faults."""
    ensure_labkit_importable()
    from labkit.mock_api import MockSession

    rng = random.Random(seed)
    def plan(n=200):
        return [rng.choice([500, 503, 429, "timeout"]) if rng.random() < fail_rate else None for _ in range(n)]
    return MockSession(faults={"/customers": plan(), "/orders": plan(), "/events": plan()})


def main(argv: list[str] | None = None) -> int:
    """Exit codes: 0 success, 1 API failure after retries."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    if args.base_url:
        import requests
        session, base_url = requests.Session(), args.base_url
        sleep = time.sleep
    else:
        session = make_mock_session(args.fail_rate, args.seed)
        from labkit.mock_api import BASE_URL
        base_url = BASE_URL
        sleep = lambda seconds: None  # noqa: E731 - the in-process mock has no real rate limit to wait for
    state = args.state or args.output / "_state.json"
    try:
        summary = run(session, base_url, args.output, state, page_size=args.page_size, sleep=sleep)
    except ApiError as exc:
        logging.getLogger("api_ingest").error("ingestion failed: %s", exc)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
