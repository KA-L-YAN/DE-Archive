"""Data-quality checks run on a pipeline's output before it is published.

Each check: func(rows, **params) -> (passed: bool, detail: str). Config: {check, severity: error|warn, ...params}.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
from collections import Counter
from .registry import CHECKS

@CHECKS.register('not_null')
def not_null(rows, column):
    """No None values in column."""
    raise NotImplementedError('TODO: implement not_null')

@CHECKS.register('unique')
def unique(rows, column):
    """No duplicate non-null values in column."""
    raise NotImplementedError('TODO: implement unique')

@CHECKS.register('row_count_min')
def row_count_min(rows, value):
    """At least `value` rows."""
    raise NotImplementedError('TODO: implement row_count_min')

@CHECKS.register('accepted_values')
def accepted_values(rows, column, values):
    """Every non-null value is in `values`."""
    raise NotImplementedError('TODO: implement accepted_values')

@CHECKS.register('range')
def value_range(rows, column, min=None, max=None):
    """All non-null values within [min, max]."""
    raise NotImplementedError('TODO: implement value_range')

def run_checks(rows: list[dict], checks: list[dict]) -> list[dict]:
    """Run configured checks; returns [{"check", "severity", "passed", "detail"}] (severity defaults to 'error')."""
    raise NotImplementedError('TODO: implement run_checks')
