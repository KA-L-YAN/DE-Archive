"""Pipeline configuration: defaults, JSON file, CLI overrides — validated once at startup."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

DEFAULT_COLUMNS = ("order_id", "customer_id", "product_id", "quantity", "unit_price", "order_ts",
                   "status", "updated_at", "channel", "country")


@dataclass(frozen=True)
class Config:
    input_dir: Path
    output_dir: Path
    pattern: str = "orders_*.csv"
    required_columns: tuple[str, ...] = DEFAULT_COLUMNS
    key: str = "order_id"
    version_column: str = "updated_at"
    max_reject_ratio: float = 0.25
    customers_file: str | None = "customers.json"
    allowed_status: tuple[str, ...] = ("PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED")
    extra: dict = field(default_factory=dict)


class ConfigError(ValueError):
    """Raised for invalid configuration."""


def validate(config: Config) -> Config:
    """Return the config if valid, else raise ConfigError describing every problem."""
    problems = []
    if not Path(config.input_dir).is_dir():
        problems.append(f"input_dir does not exist: {config.input_dir}")
    if not 0 <= config.max_reject_ratio <= 1:
        problems.append("max_reject_ratio must be between 0 and 1")
    if config.key not in config.required_columns:
        problems.append(f"key {config.key!r} must be a required column")
    if config.version_column not in config.required_columns:
        problems.append(f"version_column {config.version_column!r} must be a required column")
    if Path(config.output_dir).resolve() == Path(config.input_dir).resolve():
        problems.append("output_dir must differ from input_dir")
    if problems:
        raise ConfigError("; ".join(problems))
    return config


def load_config(path: str | Path | None = None, **overrides) -> Config:
    """Build a Config from an optional JSON file plus keyword overrides (None values ignored).

    Unknown keys in the file raise ConfigError. Lists become tuples; paths become Path objects.
    """
    data: dict = {}
    if path is not None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"cannot read config {path}: {exc}") from exc
    data.update({k: v for k, v in overrides.items() if v is not None})
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(f"unknown config keys: {unknown}")
    for name in ("required_columns", "allowed_status"):
        if name in data:
            data[name] = tuple(data[name])
    for name in ("input_dir", "output_dir"):
        if name not in data:
            raise ConfigError(f"{name} is required")
        data[name] = Path(data[name])
    return validate(Config(**data))


def with_overrides(config: Config, **changes) -> Config:
    """[provided] Copy of the config with some fields changed (re-validated)."""
    return validate(replace(config, **changes))
