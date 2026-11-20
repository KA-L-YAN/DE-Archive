"""Shared pytest configuration for the lab.

* Any test whose code raises ``NotImplementedError`` (function not written yet,
  or a project stub) is reported as SKIPPED with the message "not implemented yet".
* Run against the reference solutions with:  LAB_TARGET=solutions pytest
"""
import pytest

from labkit.testing import target


def pytest_report_header(config):
    return f"lab target: {target()}  (set LAB_TARGET=solutions to test the reference solutions)"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and call.excinfo is not None and call.excinfo.errisinstance(NotImplementedError):
        report.outcome = "skipped"
        msg = str(call.excinfo.value).splitlines()[0] if str(call.excinfo.value) else "stub"
        report.longrepr = (str(item.path), item.location[1] or 0, f"not implemented yet: {msg}")


@pytest.fixture
def no_sleep(monkeypatch):
    """Collects requested sleep durations instead of sleeping. Pass `no_sleep` as `sleep=`."""
    calls = []

    def fake_sleep(seconds):
        calls.append(seconds)

    fake_sleep.calls = calls
    return fake_sleep
