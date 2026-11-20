"""Load, resolve and validate the platform configuration (TOML)."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

SINK_MODES = {"overwrite", "append", "merge"}


class ConfigError(ValueError):
    """Invalid configuration. `.problems` lists every problem found."""

    def __init__(self, problems: list[str]):
        """[provided]"""
        super().__init__("invalid configuration:\n  - " + "\n  - ".join(problems))
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
    out = dict(platform)
    for key, value in platform.items():
        var = f"DATAPLAT_{key.upper()}"
        if var in env:
            raw = env[var]
            if isinstance(value, bool):
                out[key] = raw.lower() in ("1", "true", "yes", "on")
            elif isinstance(value, (int, float)):
                out[key] = type(value)(raw)
            else:
                out[key] = raw
    return out


def find_lab_root(start: Path) -> Path:
    """[provided] Nearest ancestor of `start` containing both `datasets/` and `labkit/` (the lab root)."""
    for parent in [start.resolve(), *start.resolve().parents]:
        if (parent / "datasets").is_dir() and (parent / "labkit").is_dir():
            return parent
    raise ConfigError([f"could not find the lab root above {start}"])


def topological_order(pipelines: dict[str, PipelineConfig]) -> list[str]:
    """Order pipelines so dependencies come first (ties alphabetical). Cycles raise ConfigError."""
    order, state = [], {}

    def visit(name, trail):
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            raise ConfigError([f"dependency cycle: {' -> '.join(trail + [name])}"])
        state[name] = "visiting"
        for dep in sorted(pipelines[name].depends_on):
            visit(dep, trail + [name])
        state[name] = "done"
        order.append(name)

    for name in sorted(pipelines):
        visit(name, [])
    return order


def load_config(path: str | Path, env: dict | None = None, overrides: dict | None = None) -> PlatformConfig:
    """Parse TOML, apply env (DATAPLAT_*) then explicit overrides to [platform], resolve paths relative to the file, validate."""
    from .registry import CHECKS, SOURCES, TRANSFORMS  # imported late so plugins are registered
    from . import quality, sources, transforms  # noqa: F401  (register built-ins)

    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError([f"cannot read {path}: {exc}"]) from exc
    base = path.parent
    platform = _env_overrides(raw.get("platform", {}), os.environ if env is None else env)
    platform.update(overrides or {})
    problems = []
    for key in ("name", "data_root", "warehouse"):
        if key not in platform:
            problems.append(f"[platform] {key} is required")
    if problems:
        raise ConfigError(problems)

    def resolve(p):
        if "{lab_root}" in str(p):
            p = str(p).replace("{lab_root}", str(find_lab_root(base)))
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    data_root = resolve(platform["data_root"])
    srcs = {}
    for name, s in raw.get("sources", {}).items():
        if s.get("type") not in SOURCES:
            problems.append(f"source {name!r}: unknown type {s.get('type')!r} (available: {SOURCES.names()})")
        options = {k: v for k, v in s.items() if k not in ("type", "path")}
        srcs[name] = SourceConfig(name, s.get("type"), (data_root / s["path"]) if "path" in s else None, options)

    pipes = {}
    for name, p in raw.get("pipelines", {}).items():
        if bool(p.get("source")) == bool(p.get("source_table")):
            problems.append(f"pipeline {name!r}: set exactly one of 'source' or 'source_table'")
        if p.get("source") and p["source"] not in srcs:
            problems.append(f"pipeline {name!r}: unknown source {p['source']!r}")
        for i, step in enumerate(p.get("steps", [])):
            if step.get("op") not in TRANSFORMS:
                problems.append(f"pipeline {name!r} step {i}: unknown op {step.get('op')!r}")
        sink = p.get("sink", {})
        if not sink.get("name"):
            problems.append(f"pipeline {name!r}: sink.name is required")
        if sink.get("mode", "overwrite") not in SINK_MODES:
            problems.append(f"pipeline {name!r}: sink.mode must be one of {sorted(SINK_MODES)}")
        if sink.get("mode") == "merge" and not sink.get("key"):
            problems.append(f"pipeline {name!r}: merge sinks need a 'key'")
        for check in p.get("quality", []):
            if check.get("check") not in CHECKS:
                problems.append(f"pipeline {name!r}: unknown quality check {check.get('check')!r}")
        pipes[name] = PipelineConfig(name=name, source=p.get("source"), source_table=p.get("source_table"), steps=list(p.get("steps", [])),
                                     sink=dict(sink), depends_on=tuple(p.get("depends_on", [])), incremental=bool(p.get("incremental", False)),
                                     quality=list(p.get("quality", [])), max_reject_ratio=p.get("max_reject_ratio"))
    for name, p in pipes.items():
        for dep in p.depends_on:
            if dep not in pipes:
                problems.append(f"pipeline {name!r}: depends on unknown pipeline {dep!r}")
    if problems:
        raise ConfigError(problems)
    topological_order(pipes)  # raises on cycles
    return PlatformConfig(name=platform["name"], data_root=data_root, warehouse=resolve(platform["warehouse"]),
                          state_dir=resolve(platform.get("state_dir", "state")), log_level=platform.get("log_level", "INFO"),
                          max_reject_ratio=float(platform.get("max_reject_ratio", 0.2)), sources=srcs, pipelines=pipes, config_path=path)
