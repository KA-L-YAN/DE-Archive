"""The execution engine: plan → per pipeline (extract → transform → quality gate → publish → commit) → run audit.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
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
log = logging.getLogger('dataplat')

class PipelineFailed(RuntimeError):
    """A pipeline failed a gate (reject ratio / quality) or raised. `.result` holds its partial result."""

    def __init__(self, message: str, result: dict):
        """[provided]"""
        super().__init__(message)
        self.result = result

@dataclass
class RunReport:
    run_id: str
    status: str = 'SUCCEEDED'
    pipelines: dict[str, dict] = field(default_factory=dict)
    started_at: str = ''
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        """[provided] JSON-friendly form."""
        return {'run_id': self.run_id, 'status': self.status, 'started_at': self.started_at, 'duration_seconds': self.duration_seconds, 'pipelines': self.pipelines}

class StateStore:
    """Per-pipeline incremental state (processed source files) + run history, as JSON files under state_dir."""

    def __init__(self, state_dir: Path):
        """Store config; create the Warehouse and StateStore it needs."""
        raise NotImplementedError('TODO: implement __init__')

    def _path(self, pipeline: str) -> Path:
        """State file for one pipeline: <state_dir>/pipelines/<name>.json."""
        raise NotImplementedError('TODO: implement _path')

    def load(self, pipeline: str) -> dict:
        """{"processed_files": {key: sha256}, "last_success": iso | None}"""
        raise NotImplementedError('TODO: implement load')

    def commit(self, pipeline: str, files: dict[str, str], run_id: str) -> None:
        """Merge newly processed files into the pipeline's state (atomic replace)."""
        raise NotImplementedError('TODO: implement commit')

    def reset(self, pipeline: str) -> None:
        """Forget incremental state (full refresh)."""
        raise NotImplementedError('TODO: implement reset')

    def save_run(self, report: RunReport) -> Path:
        """Write runs/<run_id>.json and return its path."""
        raise NotImplementedError('TODO: implement save_run')

    def runs(self) -> list[dict]:
        """All saved run reports, oldest first."""
        raise NotImplementedError('TODO: implement runs')

class Engine:

    def __init__(self, config: PlatformConfig):
        """Store config; create the Warehouse and StateStore it needs."""
        raise NotImplementedError('TODO: implement __init__')

    def plan(self, selected: list[str] | None=None) -> list[str]:
        """Execution order. With `selected`, include those pipelines and all their upstream dependencies."""
        raise NotImplementedError('TODO: implement plan')

    def _extract(self, pipe, full_refresh: bool) -> SourceBatch:
        """Read the pipeline input: a warehouse table (source_table) or a registered source, passing processed files for incremental pipelines."""
        raise NotImplementedError('TODO: implement _extract')

    def run_pipeline(self, name: str, run_id: str, dry_run: bool=False, full_refresh: bool=False) -> dict:
        """Run one pipeline; returns its result dict. Raises PipelineFailed on gate failures."""
        raise NotImplementedError('TODO: implement run_pipeline')

    def run(self, selected: list[str] | None=None, dry_run: bool=False, full_refresh: bool=False, run_id: str | None=None) -> RunReport:
        """Run the plan. A failed pipeline marks the run FAILED and its downstream pipelines UPSTREAM_FAILED; independent ones still run."""
        raise NotImplementedError('TODO: implement run')
