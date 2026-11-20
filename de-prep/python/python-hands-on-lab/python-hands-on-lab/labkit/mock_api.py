"""An in-process fake REST API with a ``requests``-compatible surface.

Use it exactly like ``requests.Session``::

    from labkit.mock_api import MockSession, BASE_URL
    session = MockSession()
    resp = session.get(f"{BASE_URL}/customers", params={"page": 1, "page_size": 50}, timeout=5)
    resp.raise_for_status()
    payload = resp.json()

Because your code only relies on ``.get/.post`` + ``.status_code/.json()/.headers``
(duck typing!), the same function works with a real ``requests.Session()`` pointed
at ``python -m labkit.mock_server``.

Endpoints
---------
GET  /customers?page=1&page_size=50     page-number pagination -> {"data", "page", "page_size", "total", "total_pages"}
GET  /customers/<id>                    single record or 404
GET  /orders?cursor=<c>&limit=100       cursor pagination      -> {"items", "next_cursor"}
GET  /products?offset=0&limit=50        link pagination        -> {"results", "next"}  (next is a full URL or None)
GET  /events?since=<iso>&limit=100      incremental feed       -> {"events", "max_updated_at"}
POST /orders  json={...}                201 created / 422 validation errors

Fault injection
---------------
``faults={"/orders": [None, 500, "timeout", 429]}`` makes the 1st call to /orders succeed,
the 2nd return HTTP 500, the 3rd raise ``requests.exceptions.Timeout``, the 4th return 429
with a ``Retry-After`` header. After the list is exhausted calls succeed. Tokens:
``None`` | int status code | ``"timeout"`` | ``"connection"``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

try:
    from requests.exceptions import ConnectionError as _ConnErr, HTTPError, Timeout
except ImportError:  # pragma: no cover - requests is in requirements.txt
    class HTTPError(Exception):
        def __init__(self, *a, response=None):
            super().__init__(*a)
            self.response = response

    class Timeout(Exception):
        pass

    class _ConnErr(Exception):
        pass

ConnectionError = _ConnErr  # noqa: A001  (mirror the requests name)

BASE_URL = "https://api.mock.local/v1"
_DATA_DIR = Path(__file__).resolve().parent.parent / "datasets" / "json" / "api"


class MockResponse:
    def __init__(self, status_code: int, payload=None, headers=None, url: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.url = url

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        return json.dumps(self._payload)

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON body")
        return copy.deepcopy(self._payload)

    def raise_for_status(self) -> None:
        if not self.ok:
            raise HTTPError(f"{self.status_code} Error for url: {self.url}", response=self)

    def __repr__(self) -> str:
        return f"<MockResponse [{self.status_code}]>"


def _load_default(name: str) -> list[dict]:
    path = _DATA_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


class MockSession:
    """Fake HTTP session. Records every call in ``self.calls`` as (method, path, params)."""

    def __init__(self, data: dict | None = None, faults: dict | None = None,
                 api_key: str | None = None, max_page_size: int = 100):
        data = data or {}
        self.data = {
            "customers": data.get("customers", _load_default("customers") if not data else []),
            "orders": data.get("orders", _load_default("orders") if not data else []),
            "products": data.get("products", _load_default("products") if not data else []),
            "events": data.get("events", _load_default("events") if not data else []),
        }
        self.faults = {k: list(v) for k, v in (faults or {}).items()}
        self.api_key = api_key
        self.max_page_size = max_page_size
        self.calls: list[tuple[str, str, dict]] = []
        self.headers: dict[str, str] = {}
        self._next_order_id = 900000

    # -- requests-like API -------------------------------------------------
    def get(self, url, params=None, timeout=None, headers=None, **_):
        return self._handle("GET", url, params or {}, None, headers or {})

    def post(self, url, json=None, params=None, timeout=None, headers=None, **_):  # noqa: A002
        return self._handle("POST", url, params or {}, json, headers or {})

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- internals ----------------------------------------------------------
    def _handle(self, method, url, params, body, headers):
        parsed = urlparse(url)
        path = parsed.path
        if path.startswith("/v1"):
            path = path[3:]
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        query.update({k: v for k, v in params.items() if v is not None})
        self.calls.append((method, path, dict(query)))

        fault_key = "/" + path.strip("/").split("/")[0]
        queue = self.faults.get(path) or self.faults.get(fault_key)
        if queue:
            token = queue.pop(0)
            if token == "timeout":
                raise Timeout(f"Read timed out: {url}")
            if token == "connection":
                raise ConnectionError(f"Connection refused: {url}")
            if isinstance(token, int):
                hdrs = {"Retry-After": "1"} if token == 429 else {}
                return MockResponse(token, {"error": f"simulated {token}"}, hdrs, url)

        if self.api_key is not None:
            auth = {**self.headers, **headers}.get("Authorization")
            if auth != f"Bearer {self.api_key}":
                return MockResponse(401, {"error": "unauthorized"}, url=url)

        try:
            return self._route(method, path, query, body, url)
        except (ValueError, TypeError) as exc:
            return MockResponse(400, {"error": f"bad request: {exc}"}, url=url)

    def _route(self, method, path, q, body, url):
        parts = [p for p in path.split("/") if p]
        if method == "GET" and parts == ["customers"]:
            page, size = int(q.get("page", 1)), min(int(q.get("page_size", 50)), self.max_page_size)
            if page < 1 or size < 1:
                raise ValueError("page and page_size must be >= 1")
            rows = self.data["customers"]
            total_pages = max(1, -(-len(rows) // size))
            chunk = rows[(page - 1) * size: page * size]
            return MockResponse(200, {"data": chunk, "page": page, "page_size": size,
                                      "total": len(rows), "total_pages": total_pages}, url=url)
        if method == "GET" and len(parts) == 2 and parts[0] == "customers":
            for row in self.data["customers"]:
                if str(row.get("customer_id")) == parts[1]:
                    return MockResponse(200, row, url=url)
            return MockResponse(404, {"error": "customer not found"}, url=url)
        if method == "GET" and parts == ["orders"]:
            limit = min(int(q.get("limit", 100)), self.max_page_size)
            cursor = q.get("cursor")
            start = 0
            if cursor:
                if not str(cursor).startswith("c_"):
                    raise ValueError("invalid cursor")
                start = int(str(cursor)[2:])
            rows = self.data["orders"]
            chunk = rows[start:start + limit]
            nxt = f"c_{start + limit}" if start + limit < len(rows) else None
            return MockResponse(200, {"items": chunk, "next_cursor": nxt}, url=url)
        if method == "GET" and parts == ["products"]:
            offset, limit = int(q.get("offset", 0)), min(int(q.get("limit", 50)), self.max_page_size)
            rows = self.data["products"]
            nxt = None
            if offset + limit < len(rows):
                nxt = f"{BASE_URL}/products?" + urlencode({"offset": offset + limit, "limit": limit})
            return MockResponse(200, {"results": rows[offset:offset + limit], "next": nxt}, url=url)
        if method == "GET" and parts == ["events"]:
            since = q.get("since") or ""
            limit = min(int(q.get("limit", 100)), self.max_page_size)
            rows = sorted((e for e in self.data["events"] if e.get("updated_at", "") > since),
                          key=lambda e: e["updated_at"])[:limit]
            max_ts = rows[-1]["updated_at"] if rows else None
            return MockResponse(200, {"events": rows, "max_updated_at": max_ts}, url=url)
        if method == "POST" and parts == ["orders"]:
            errors = []
            if not isinstance(body, dict):
                return MockResponse(400, {"error": "JSON object body required"}, url=url)
            if not body.get("customer_id"):
                errors.append("customer_id is required")
            items = body.get("items")
            if not isinstance(items, list) or not items:
                errors.append("items must be a non-empty list")
            if errors:
                return MockResponse(422, {"errors": errors}, url=url)
            self._next_order_id += 1
            return MockResponse(201, {"order_id": self._next_order_id, **body}, url=url)
        return MockResponse(404, {"error": f"no route for {method} {path}"}, url=url)
