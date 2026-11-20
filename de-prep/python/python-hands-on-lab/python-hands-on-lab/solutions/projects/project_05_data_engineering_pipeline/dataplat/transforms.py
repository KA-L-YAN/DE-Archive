"""Built-in transforms. Signature: func(records: list[dict], ctx: StepContext, **params) -> list[dict].

Transforms never mutate input dicts. Rows that fail validation go to `ctx.rejects` (with `_errors`).
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable

from .registry import TRANSFORMS


@dataclass
class StepContext:
    """Per-pipeline-run context handed to every transform."""
    read_table: Callable[[str], list[dict]]
    rejects: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# ------------------------------------------------------------------ helpers
_TRUE, _FALSE = {"true", "1", "yes", "y"}, {"false", "0", "no", "n"}


def to_bool(v):
    """[provided] Lenient bool parser; None/blank -> None; unknown text -> ValueError."""
    if v is None or isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if not s:
        return None
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    raise ValueError(f"not a boolean: {v!r}")


def to_timestamp(v) -> str | None:
    """ISO-8601 (Z or offset or naive=UTC) -> canonical 'YYYY-MM-DDTHH:MM:SSZ'; blank -> None; invalid -> ValueError."""
    if v is None or str(v).strip() == "":
        return None
    dt = datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_date(v) -> str | None:
    """'YYYY-MM-DD' or 'DD/MM/YYYY' -> ISO date string; blank -> None; invalid -> ValueError."""
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"not a date: {v!r}")


CASTS = {"int": lambda v: None if str(v).strip() == "" else int(str(v).strip()),
         "float": lambda v: None if str(v).strip() == "" else float(str(v).strip()),
         "str": lambda v: None if v is None else str(v), "bool": to_bool, "timestamp": to_timestamp, "date": to_date}


# ------------------------------------------------------------------ column ops
@TRANSFORMS.register("rename")
def rename(records, ctx, mapping):
    """Rename keys per `mapping`."""
    return [{mapping.get(k, k): v for k, v in r.items()} for r in records]


@TRANSFORMS.register("select")
def select(records, ctx, columns):
    """Keep only `columns` (missing -> None), in that order, plus any `_`-prefixed lineage columns."""
    return [{**{c: r.get(c) for c in columns}, **{k: v for k, v in r.items() if k.startswith("_")}} for r in records]


@TRANSFORMS.register("strip")
def strip(records, ctx, columns):
    """Strip whitespace (and collapse inner whitespace) in string columns; blank -> None."""
    def clean(v):
        if not isinstance(v, str):
            return v
        s = " ".join(v.split())
        return s or None
    return [{**r, **{c: clean(r.get(c)) for c in columns if c in r}} for r in records]


def _case(records, columns, method):
    """Apply str method `method` (upper/lower/title) to the given string columns."""
    return [{**r, **{c: getattr(r[c], method)() for c in columns if isinstance(r.get(c), str)}} for r in records]


@TRANSFORMS.register("upper")
def upper(records, ctx, columns):
    """Uppercase string columns."""
    return _case(records, columns, "upper")


@TRANSFORMS.register("lower")
def lower(records, ctx, columns):
    """Lowercase string columns."""
    return _case(records, columns, "lower")


@TRANSFORMS.register("title")
def title(records, ctx, columns):
    """Title-case string columns."""
    return _case(records, columns, "title")


@TRANSFORMS.register("cast")
def cast(records, ctx, column, to):
    """Cast a column with CASTS[to]; failures reject the row (error '<column>: cannot cast to <to>')."""
    fn = CASTS[to]
    out = []
    for r in records:
        try:
            out.append({**r, column: fn(r.get(column))})
        except (TypeError, ValueError):
            ctx.rejects.append({**r, "_errors": [f"{column}: cannot cast to {to}"]})
    return out


@TRANSFORMS.register("fill_null")
def fill_null(records, ctx, columns, value):
    """Replace None (or missing) values in `columns` with `value`."""
    return [{**r, **{c: value for c in columns if r.get(c) is None}} for r in records]


# ------------------------------------------------------------------ validation
def _rule_error(rule, value):
    """Error message for one validation rule applied to value, or None if it passes (None values only fail 'required')."""
    check = rule["check"]
    if check == "required":
        return None if value not in (None, "") else "is required"
    if value is None:
        return None
    if check == "min":
        return None if value >= rule["value"] else f"below min {rule['value']}"
    if check == "max":
        return None if value <= rule["value"] else f"above max {rule['value']}"
    if check == "in":
        return None if value in rule["values"] else "not an allowed value"
    if check == "regex":
        return None if re.fullmatch(rule["pattern"], str(value)) else "does not match pattern"
    raise KeyError(f"unknown validation check {check!r}")


@TRANSFORMS.register("validate")
def validate(records, ctx, rules):
    """Apply every rule ({column, check: required|min|max|in|regex, ...}); rows with any error go to ctx.rejects with all errors."""
    out = []
    for r in records:
        errors = [f"{rule['column']}: {err}" for rule in rules if (err := _rule_error(rule, r.get(rule["column"])))]
        if errors:
            ctx.rejects.append({**r, "_errors": errors})
        else:
            out.append(r)
    return out


# ------------------------------------------------------------------ row ops
EXPRESSIONS = {
    "multiply": lambda *xs: round(_product(xs), 2) if all(x is not None for x in xs) else None,
    "date_of": lambda ts: ts[:10] if ts else None,
    "concat": lambda *xs: "".join("" if x is None else str(x) for x in xs),
    "coalesce": lambda *xs: next((x for x in xs if x is not None), None),
    "email_domain": lambda e: e.split("@", 1)[1] if e and "@" in e else None,
}


def _product(xs):
    """Product of numbers."""
    result = 1
    for x in xs:
        result *= x
    return result


@TRANSFORMS.register("derive")
def derive(records, ctx, column, expr, args):
    """New column = EXPRESSIONS[expr](*[row[a] for a in args])."""
    fn = EXPRESSIONS[expr]
    return [{**r, column: fn(*(r.get(a) for a in args))} for r in records]


_OPS = {"=": lambda a, b: a == b, "!=": lambda a, b: a != b, ">": lambda a, b: a is not None and a > b,
        ">=": lambda a, b: a is not None and a >= b, "<": lambda a, b: a is not None and a < b,
        "<=": lambda a, b: a is not None and a <= b, "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b}


@TRANSFORMS.register("filter")
def filter_rows(records, ctx, column, operator, value):
    """Keep rows where `row[column] <operator> value` (operators: = != > >= < <= in not_in)."""
    op = _OPS[operator]
    return [r for r in records if op(r.get(column), value)]


@TRANSFORMS.register("dedupe")
def dedupe(records, ctx, key, order_by=None, keep="last"):
    """One row per key tuple. With order_by: keep the greatest ('last') or smallest ('first') value (None sorts lowest).
    Without order_by: keep first or last occurrence. Output in first-appearance order of keys. Removed count -> ctx.stats['duplicates']."""
    keys = [key] if isinstance(key, str) else list(key)
    best: dict[tuple, dict] = {}
    for r in records:
        k = tuple(r.get(c) for c in keys)
        current = best.get(k)
        if current is None:
            best[k] = r
            continue
        if order_by is None:
            if keep == "last":
                best[k] = r
            continue
        a, b = r.get(order_by), current.get(order_by)
        if a is not None and (b is None or (a >= b if keep == "last" else a < b)):
            best[k] = r
    ctx.stats["duplicates"] = ctx.stats.get("duplicates", 0) + len(records) - len(best)
    return list(best.values())


@TRANSFORMS.register("lookup")
def lookup(records, ctx, table, key, columns, prefix="", default=None, require_match=False):
    """Left-join columns from a warehouse table by `key` (one row per key expected). With require_match, unmatched rows are rejected."""
    index = {row[key]: row for row in ctx.read_table(table)}
    out = []
    for r in records:
        match = index.get(r.get(key))
        if match is None and require_match:
            ctx.rejects.append({**r, "_errors": [f"{key}: no match in {table}"]})
            continue
        out.append({**r, **{f"{prefix}{c}": (match.get(c) if match else default) for c in columns}})
    return out


AGGREGATES = {
    "count": lambda vals: len(vals),
    "count_distinct": lambda vals: len({v for v in vals if v is not None}),
    "sum": lambda vals: round(sum(v for v in vals if v is not None), 2),
    "min": lambda vals: min((v for v in vals if v is not None), default=None),
    "max": lambda vals: max((v for v in vals if v is not None), default=None),
    "avg": lambda vals: (round(sum(p) / len(p), 2) if (p := [v for v in vals if v is not None]) else None),
}


@TRANSFORMS.register("aggregate")
def aggregate(records, ctx, group_by, metrics):
    """Group by columns; metrics = {out_name: {fn, column}}. Output sorted by group key."""
    groups = defaultdict(list)
    for r in records:
        groups[tuple(r.get(c) for c in group_by)].append(r)
    out = []
    for k in sorted(groups, key=lambda t: tuple("" if x is None else x for x in t)):
        rows = groups[k]
        row = dict(zip(group_by, k))
        for name, m in metrics.items():
            row[name] = AGGREGATES[m["fn"]]([x.get(m.get("column")) for x in rows])
        out.append(row)
    return out
