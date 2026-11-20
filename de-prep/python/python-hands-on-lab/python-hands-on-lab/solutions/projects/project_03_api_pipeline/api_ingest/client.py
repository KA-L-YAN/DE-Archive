"""A small resilient HTTP client: retries with backoff, Retry-After support, metrics."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger("api_ingest.client")
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class ApiError(Exception):
    """Non-retryable API failure, or retries exhausted. `.status` is the HTTP status (None for network errors)."""

    def __init__(self, message: str, status: int | None = None):
        """[provided]"""
        super().__init__(message)
        self.status = status


class ApiClient:
    """Wraps any requests-like session (`requests.Session` or `labkit.mock_api.MockSession`)."""

    def __init__(self, session, base_url: str, max_attempts: int = 4, base_delay: float = 0.5,
                 timeout: float = 10, sleep=time.sleep):
        """Store the session/settings and initialise metrics = {'requests': 0, 'retries': 0, 'failures': 0}."""
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.timeout = timeout
        self.sleep = sleep
        self.metrics = {"requests": 0, "retries": 0, "failures": 0}

    def _wait(self, attempt: int, retry_after: str | None) -> None:
        """Count a retry and sleep: Retry-After seconds if numeric, else base_delay * 2 ** (attempt - 1)."""
        delay = float(retry_after) if retry_after and retry_after.isdigit() else self.base_delay * 2 ** (attempt - 1)
        self.metrics["retries"] += 1
        self.sleep(delay)

    def get_json(self, path: str, params: dict | None = None) -> dict:
        """GET base_url/path and return parsed JSON, retrying transient failures.

        Retries on RETRYABLE_STATUS, requests.Timeout and requests.ConnectionError, up to
        `max_attempts` attempts, waiting `Retry-After` seconds when provided else exponential backoff.
        Raises ApiError for non-retryable statuses or when attempts are exhausted.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(1, self.max_attempts + 1):
            self.metrics["requests"] += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                log.warning("attempt %d/%d for %s failed: %s", attempt, self.max_attempts, path, exc)
                if attempt == self.max_attempts:
                    self.metrics["failures"] += 1
                    raise ApiError(f"network error after {attempt} attempts: {exc}") from exc
                self._wait(attempt, None)
                continue
            if resp.status_code < 400:
                return resp.json()
            if resp.status_code not in RETRYABLE_STATUS or attempt == self.max_attempts:
                self.metrics["failures"] += 1
                raise ApiError(f"HTTP {resp.status_code} for {path}", resp.status_code)
            log.warning("attempt %d/%d for %s got HTTP %d", attempt, self.max_attempts, path, resp.status_code)
            self._wait(attempt, resp.headers.get("Retry-After"))
        raise AssertionError("unreachable")
