"""Tests for 06_files_json_csv/04_logging.ipynb

Run: pytest tests/files/test_06_04_logging.py -v
"""
import pytest

from labkit.testing import load

nb = load("06_files_json_csv/04_logging.ipynb")


def test_get_logger_idempotent():
    import io, logging
    buf = io.StringIO()
    lg = nb.get_logger("lab.test.idem", "DEBUG", stream=buf)
    lg2 = nb.get_logger("lab.test.idem", "WARNING", stream=buf)
    assert lg is lg2 and len(lg.handlers) == 1 and lg.level == logging.WARNING and lg.propagate is False
    lg.warning("hello %s", "world")
    out = buf.getvalue()
    assert "WARNING lab.test.idem - hello world" in out and out.count("hello") == 1


def test_file_logger_rotation(tmp_path):
    lg = nb.file_logger("lab_rot_test", tmp_path / "logs", max_bytes=300, backups=2)
    nb.file_logger("lab_rot_test", tmp_path / "logs", max_bytes=300, backups=2)
    from logging.handlers import RotatingFileHandler
    assert sum(isinstance(h, RotatingFileHandler) for h in lg.handlers) == 1
    for i in range(50):
        lg.info("message number %d with padding", i)
    for h in lg.handlers:
        h.flush()
    files = sorted(p.name for p in (tmp_path / "logs").iterdir())
    assert files == ["lab_rot_test.log", "lab_rot_test.log.1", "lab_rot_test.log.2"]
    for h in list(lg.handlers):
        h.close(); lg.removeHandler(h)


def test_json_formatter():
    import io, json, logging
    buf = io.StringIO()
    lg = logging.getLogger("lab.test.json"); lg.handlers.clear(); lg.propagate = False; lg.setLevel(logging.INFO)
    h = logging.StreamHandler(buf); h.setFormatter(nb.JsonFormatter()); lg.addHandler(h)
    lg.info("loaded %d rows", 10, extra={"run_id": "r1", "path": object.__new__(object)})
    try:
        1 / 0
    except ZeroDivisionError:
        lg.exception("failed")
    first, second = [json.loads(l) for l in buf.getvalue().splitlines()]
    assert first["message"] == "loaded 10 rows" and first["run_id"] == "r1" and first["level"] == "INFO" and first["ts"].endswith("Z")
    assert isinstance(first["path"], str) and "lineno" not in first
    assert second["level"] == "ERROR" and "ZeroDivisionError" in second["exc"]


def test_log_context(caplog):
    import logging
    lg = logging.getLogger("lab.test.ctx"); lg.setLevel(logging.INFO); lg.propagate = True
    with caplog.at_level(logging.INFO, logger="lab.test.ctx"):
        with nb.log_context(lg, run_id="r1", file="a.csv"):
            lg.info("outer")
            with nb.log_context(lg, file="b.csv"):
                lg.info("inner")
                lg.info("explicit", extra={"file": "z.csv"})
            lg.info("outer again")
        lg.info("outside")
    recs = {r.getMessage(): r for r in caplog.records}
    assert (recs["outer"].run_id, recs["outer"].file) == ("r1", "a.csv")
    assert (recs["inner"].run_id, recs["inner"].file) == ("r1", "b.csv") and recs["explicit"].file == "z.csv"
    assert recs["outer again"].file == "a.csv" and not hasattr(recs["outside"], "run_id") and lg.filters == []

def test_log_context_cleanup_on_error():
    import logging
    lg = logging.getLogger("lab.test.ctx2")
    log_context = nb.log_context
    class Boom(Exception):
        pass
    with pytest.raises(Boom):
        with log_context(lg, run_id="x"):
            raise Boom
    assert lg.filters == []


class FakeClock:
    def __init__(self): self.t = 0.0
    def __call__(self):
        self.t += 0.25
        return self.t

def test_run_steps_success(caplog):
    import logging
    lg = logging.getLogger("lab.test.steps")
    def extract(ctx): ctx["rows"] = [1, 2, 3]; return 3
    def transform(ctx): ctx["rows"] = [r * 2 for r in ctx["rows"]]; return len(ctx["rows"])
    def report(ctx): return None
    with caplog.at_level(logging.INFO, logger="lab.test.steps"):
        r = nb.run_steps([("extract", extract), ("transform", transform), ("report", report)], lg, "run-1", clock=FakeClock())
    assert r["status"] == "SUCCESS" and r["total_rows"] == 6 and [s["duration_ms"] for s in r["steps"]] == [250, 250, 250]
    finished = [rec for rec in caplog.records if rec.getMessage() == "step finished"]
    assert [(f.step, f.rows, f.run_id) for f in finished] == [("extract", 3, "run-1"), ("transform", 3, "run-1"), ("report", None, "run-1")]

def test_run_steps_failure(caplog):
    import logging
    lg = logging.getLogger("lab.test.steps2")
    def boom(ctx): raise KeyError("missing column")
    with caplog.at_level(logging.INFO, logger="lab.test.steps2"):
        r = nb.run_steps([("a", lambda c: 1), ("b", boom), ("c", lambda c: 1)], lg, "run-2", clock=FakeClock())
    assert r["status"] == "FAILED" and [s["status"] for s in r["steps"]] == ["success", "failed", "skipped"]
    assert r["steps"][1]["error"] == "KeyError: 'missing column'" and r["total_rows"] == 1
    err = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(err) == 1 and err[0].exc_info and err[0].step == "b"
