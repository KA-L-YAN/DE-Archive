"""The execution engine: plan → per pipeline (extract → transform → quality gate → publish → commit) → run audit."""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import PlatformConfig, topological_order
from .quality import run_checks
from .registry import SOURCES, TRANSFORMS
from .sources import SourceBatch
from .transforms import StepContext
from .warehouse import Warehouse

log = logging.getLogger("dataplat")


class PipelineFailed(RuntimeError):
    """A pipeline failed a gate (reject ratio / quality) or raised. `.result` holds its partial result."""

    def __init__(self, message: str, result: dict):
        """[provided]"""
        super().__init__(message)
        self.result = result


@dataclass
class RunReport:
    run_id: str
    status: str = "SUCCEEDED"
    pipelines: dict[str, dict] = field(default_factory=dict)
    started_at: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        """[provided] JSON-friendly form."""
        return {"run_id": self.run_id, "status": self.status, "started_at": self.started_at,
                "duration_seconds": self.duration_seconds, "pipelines": self.pipelines}


class StateStore:
    """Per-pipeline incremental state (processed source files) + run history, as JSON files under state_dir."""

    def __init__(self, state_dir: Path):
        """Store config; create the Warehouse and StateStore it needs."""
        self.dir = Path(state_dir)

    def _path(self, pipeline: str) -> Path:
        """State file for one pipeline: <state_dir>/pipelines/<name>.json."""
        return self.dir / "pipelines" / f"{pipeline}.json"

    def load(self, pipeline: str) -> dict:
        """{"processed_files": {key: sha256}, "last_success": iso | None}"""
        p = self._path(pipeline)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"processed_files": {}, "last_success": None}

    def commit(self, pipeline: str, files: dict[str, str], run_id: str) -> None:
        """Merge newly processed files into the pipeline's state (atomic replace)."""
        state = self.load(pipeline)
        state["processed_files"].update(files)
        state["last_success"] = run_id
        p = self._path(pipeline)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
        tmp.replace(p)

    def reset(self, pipeline: str) -> None:
        """Forget incremental state (full refresh)."""
        self._path(pipeline).unlink(missing_ok=True)

    def save_run(self, report: RunReport) -> Path:
        """Write runs/<run_id>.json and return its path."""
        p = self.dir / "runs" / f"{report.run_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return p

    def runs(self) -> list[dict]:
        """All saved run reports, oldest first."""
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.dir / "runs").glob("*.json"), key=lambda p: p.stat().st_mtime)] \
            if (self.dir / "runs").exists() else []


class Engine:
    def __init__(self, config: PlatformConfig):
        """Store config; create the Warehouse and StateStore it needs."""
        self.config = config
        self.warehouse = Warehouse(config.warehouse)
        self.state = StateStore(config.state_dir)

    def plan(self, selected: list[str] | None = None) -> list[str]:
        """Execution order. With `selected`, include those pipelines and all their upstream dependencies."""
        order = topological_order(self.config.pipelines)
        if not selected:
            return order
        unknown = [s for s in selected if s not in self.config.pipelines]
        if unknown:
            raise KeyError(f"unknown pipelines: {unknown}")
        needed, stack = set(), list(selected)
        while stack:
            name = stack.pop()
            if name not in needed:
                needed.add(name)
                stack.extend(self.config.pipelines[name].depends_on)
        return [n for n in order if n in needed]

    def _extract(self, pipe, full_refresh: bool) -> SourceBatch:
        """Read the pipeline input: a warehouse table (source_table) or a registered source, passing processed files for incremental pipelines."""
        if pipe.source_table:
            return SourceBatch(records=self.warehouse.read(pipe.source_table))
        src = self.config.sources[pipe.source]
        processed = None
        if pipe.incremental and not full_refresh:
            processed = self.state.load(pipe.name)["processed_files"]
        return SOURCES.get(src.type)(src, processed)

    def run_pipeline(self, name: str, run_id: str, dry_run: bool = False, full_refresh: bool = False) -> dict:
        """Run one pipeline; returns its result dict. Raises PipelineFailed on gate failures."""
        pipe = self.config.pipelines[name]
        t0 = time.perf_counter()
        result = {"status": "RUNNING", "rows_in": 0, "rows_out": 0, "rejected": 0, "duplicates": 0, "files": [], "skipped_files": [],
                  "quality": [], "published": False}
        if full_refresh and pipe.incremental:
            self.state.reset(name)
        batch = self._extract(pipe, full_refresh)
        result.update(rows_in=len(batch.records), files=sorted(batch.files), skipped_files=batch.skipped_files, malformed=batch.malformed)
        ctx = StepContext(read_table=self.warehouse.read)
        rows = batch.records
        for step in pipe.steps:
            params = {k: v for k, v in step.items() if k != "op"}
            rows = TRANSFORMS.get(step["op"])(rows, ctx, **params)
        result.update(rows_out=len(rows), rejected=len(ctx.rejects), duplicates=ctx.stats.get("duplicates", 0))
        limit = pipe.max_reject_ratio if pipe.max_reject_ratio is not None else self.config.max_reject_ratio
        ratio = len(ctx.rejects) / len(batch.records) if batch.records else 0.0
        result["reject_ratio"] = round(ratio, 4)
        if not dry_run and (ctx.rejects or not pipe.incremental):
            # incremental pipelines accumulate rejects per run; full-refresh pipelines replace them (idempotent reruns)
            self.warehouse.write(f"_rejects_{name}", [{**r, "errors": r.get("_errors"), "run_id": run_id} for r in ctx.rejects],
                                 mode="append" if pipe.incremental else "overwrite")
        if ratio > limit:
            result["status"] = "FAILED"
            raise PipelineFailed(f"{name}: reject ratio {ratio:.2%} exceeds {limit:.2%}", result)
        incremental_noop = pipe.incremental and not batch.files and not full_refresh
        if not incremental_noop:
            check_rows = rows
            sink = pipe.sink
            if sink.get("mode") == "merge" and self.warehouse.exists(sink["name"]):
                check_rows = None  # checked after merge on the full table
            if check_rows is not None:
                result["quality"] = run_checks(check_rows, pipe.quality)
                if any(not q["passed"] and q["severity"] == "error" for q in result["quality"]):
                    result["status"] = "FAILED"
                    raise PipelineFailed(f"{name}: quality checks failed", result)
            if not dry_run:
                write = self.warehouse.write(sink["name"], rows, mode=sink.get("mode", "overwrite"), partition_by=sink.get("partition_by"),
                                             key=sink.get("key"), version=sink.get("version"))
                result.update(published=True, partitions_written=write["partitions"])
                if check_rows is None:
                    result["quality"] = run_checks(self.warehouse.read(sink["name"]), pipe.quality)
                    if any(not q["passed"] and q["severity"] == "error" for q in result["quality"]):
                        result["status"] = "FAILED"
                        raise PipelineFailed(f"{name}: quality checks failed after merge", result)
                if pipe.incremental:
                    self.state.commit(name, batch.files, run_id)
        result["status"] = "SKIPPED_NO_NEW_DATA" if incremental_noop else ("DRY_RUN" if dry_run else "SUCCEEDED")
        result["duration_seconds"] = round(time.perf_counter() - t0, 3)
        log.info(json.dumps({"event": "pipeline_finished", "run_id": run_id, "pipeline": name, "status": result["status"],
                             "rows_in": result["rows_in"], "rows_out": result["rows_out"], "rejected": result["rejected"]}))
        return result

    def run(self, selected: list[str] | None = None, dry_run: bool = False, full_refresh: bool = False,
            run_id: str | None = None) -> RunReport:
        """Run the plan. A failed pipeline marks the run FAILED and its downstream pipelines UPSTREAM_FAILED; independent ones still run."""
        report = RunReport(run_id=run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6],
                           started_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        t0 = time.perf_counter()
        failed: set[str] = set()
        for name in self.plan(selected):
            deps = self.config.pipelines[name].depends_on
            if any(d in failed for d in deps):
                report.pipelines[name] = {"status": "UPSTREAM_FAILED"}
                failed.add(name)
                continue
            try:
                report.pipelines[name] = self.run_pipeline(name, report.run_id, dry_run=dry_run, full_refresh=full_refresh)
            except PipelineFailed as exc:
                report.pipelines[name] = {**exc.result, "error": str(exc)}
                failed.add(name)
            except Exception as exc:  # unexpected bug in a step: record and continue with independent pipelines
                log.exception("pipeline %s crashed", name)
                report.pipelines[name] = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
                failed.add(name)
        report.status = "FAILED" if failed else "SUCCEEDED"
        report.duration_seconds = round(time.perf_counter() - t0, 3)
        if not dry_run:
            self.state.save_run(report)
        return report
