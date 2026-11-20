"""A small resilient HTTP client: retries with backoff, Retry-After support, metrics.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import logging
import time
import requests
log = logging.getLogger('api_ingest.client')
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

class ApiError(Exception):
    """Non-retryable API failure, or retries exhausted. `.status` is the HTTP status (None for network errors)."""

    def __init__(self, message: str, status: int | None=None):
        """[provided]"""
        super().__init__(message)
        self.status = status

class ApiClient:
    """Wraps any requests-like session (`requests.Session` or `labkit.mock_api.MockSession`)."""

    def __init__(self, session, base_url: str, max_attempts: int=4, base_delay: float=0.5, timeout: float=10, sleep=time.sleep):
        """Store the session/settings and initialise metrics = {'requests': 0, 'retries': 0, 'failures': 0}."""
        raise NotImplementedError('TODO: implement __init__')

    def _wait(self, attempt: int, retry_after: str | None) -> None:
        """Count a retry and sleep: Retry-After seconds if numeric, else base_delay * 2 ** (attempt - 1)."""
        raise NotImplementedError('TODO: implement _wait')

    def get_json(self, path: str, params: dict | None=None) -> dict:
        """GET base_url/path and return parsed JSON, retrying transient failures.

        Retries on RETRYABLE_STATUS, requests.Timeout and requests.ConnectionError, up to
        `max_attempts` attempts, waiting `Retry-After` seconds when provided else exponential backoff.
        Raises ApiError for non-retryable statuses or when attempts are exhausted.
        """
        raise NotImplementedError('TODO: implement get_json')
