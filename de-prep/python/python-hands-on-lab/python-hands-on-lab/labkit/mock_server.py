"""Serve the mock API over real HTTP on localhost so you can practise with ``requests``.

    python -m labkit.mock_server --port 8765 --fail-rate 0.1

Then, in a notebook::

    import requests
    r = requests.get("http://127.0.0.1:8765/v1/customers", params={"page": 1}, timeout=5)

``--fail-rate`` randomly returns 500/429 responses so you can exercise retry logic.
No internet access is needed - everything runs on your machine.
"""
from __future__ import annotations

import argparse
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from labkit.mock_api import MockSession


def make_handler(session: MockSession, fail_rate: float, rng: random.Random):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, resp):
            body = resp.text.encode()
            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _maybe_fail(self) -> bool:
            if rng.random() < fail_rate:
                code = rng.choice([500, 503, 429])
                body = json.dumps({"error": f"simulated {code}"}).encode()
                self.send_response(code)
                if code == 429:
                    self.send_header("Retry-After", "1")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return True
            return False

        def do_GET(self):  # noqa: N802
            if not self._maybe_fail():
                self._send(session.get("http://local" + self.path, headers=dict(self.headers)))

        def do_POST(self):  # noqa: N802
            if self._maybe_fail():
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = None
            self._send(session.post("http://local" + self.path, json=payload, headers=dict(self.headers)))

        def log_message(self, fmt, *args):
            print(f"[mock-api] {self.address_string()} {fmt % args}")

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local mock REST API for the lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fail-rate", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port),
                                 make_handler(MockSession(), args.fail_rate, random.Random(args.seed)))
    print(f"Mock API on http://{args.host}:{args.port}/v1  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
