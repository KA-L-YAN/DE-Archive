"""Pipeline configuration: defaults, JSON file, CLI overrides — validated once at startup.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
DEFAULT_COLUMNS = ('order_id', 'customer_id', 'product_id', 'quantity', 'unit_price', 'order_ts', 'status', 'updated_at', 'channel', 'country')

@dataclass(frozen=True)
class Config:
    input_dir: Path
    output_dir: Path
    pattern: str = 'orders_*.csv'
    required_columns: tuple[str, ...] = DEFAULT_COLUMNS
    key: str = 'order_id'
    version_column: str = 'updated_at'
    max_reject_ratio: float = 0.25
    customers_file: str | None = 'customers.json'
    allowed_status: tuple[str, ...] = ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED')
    extra: dict = field(default_factory=dict)

class ConfigError(ValueError):
    """Raised for invalid configuration."""

def validate(config: Config) -> Config:
    """Return the config if valid, else raise ConfigError describing every problem."""
    raise NotImplementedError('TODO: implement validate')

def load_config(path: str | Path | None=None, **overrides) -> Config:
    """Build a Config from an optional JSON file plus keyword overrides (None values ignored).

    Unknown keys in the file raise ConfigError. Lists become tuples; paths become Path objects.
    """
    raise NotImplementedError('TODO: implement load_config')

def with_overrides(config: Config, **changes) -> Config:
    """[provided] Copy of the config with some fields changed (re-validated)."""
    return validate(replace(config, **changes))
