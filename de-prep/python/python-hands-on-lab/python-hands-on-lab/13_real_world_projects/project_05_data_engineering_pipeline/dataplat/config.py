"""Load, resolve and validate the platform configuration (TOML).

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
SINK_MODES = {'overwrite', 'append', 'merge'}

class ConfigError(ValueError):
    """Invalid configuration. `.problems` lists every problem found."""

    def __init__(self, problems: list[str]):
        """[provided]"""
        super().__init__('invalid configuration:\n  - ' + '\n  - '.join(problems))
        self.problems = problems

@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    path: Path | None = None
    options: dict = field(default_factory=dict)

@dataclass(frozen=True)
class PipelineConfig:
    name: str
    source: str | None
    source_table: str | None
    steps: list[dict]
    sink: dict
    depends_on: tuple[str, ...] = ()
    incremental: bool = False
    quality: list[dict] = field(default_factory=list)
    max_reject_ratio: float | None = None

@dataclass(frozen=True)
class PlatformConfig:
    name: str
    data_root: Path
    warehouse: Path
    state_dir: Path
    log_level: str
    max_reject_ratio: float
    sources: dict[str, SourceConfig]
    pipelines: dict[str, PipelineConfig]
    config_path: Path | None = None

def _env_overrides(platform: dict, env: dict) -> dict:
    """DATAPLAT_<KEY>=value overrides keys of the [platform] table (coerced to the existing value's type)."""
    raise NotImplementedError('TODO: implement _env_overrides')

def find_lab_root(start: Path) -> Path:
    """[provided] Nearest ancestor of `start` containing both `datasets/` and `labkit/` (the lab root)."""
    for parent in [start.resolve(), *start.resolve().parents]:
        if (parent / 'datasets').is_dir() and (parent / 'labkit').is_dir():
            return parent
    raise ConfigError([f'could not find the lab root above {start}'])

def topological_order(pipelines: dict[str, PipelineConfig]) -> list[str]:
    """Order pipelines so dependencies come first (ties alphabetical). Cycles raise ConfigError."""
    raise NotImplementedError('TODO: implement topological_order')

def load_config(path: str | Path, env: dict | None=None, overrides: dict | None=None) -> PlatformConfig:
    """Parse TOML, apply env (DATAPLAT_*) then explicit overrides to [platform], resolve paths relative to the file, validate."""
    raise NotImplementedError('TODO: implement load_config')
