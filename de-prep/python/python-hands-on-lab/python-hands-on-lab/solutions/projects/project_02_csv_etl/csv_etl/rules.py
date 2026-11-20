"""Validation, cleaning, transformation, dedup and aggregation — pure functions, no I/O."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable


class ValidationError(ValueError):
    """A row failed validation. `field` names the first offending column."""

    def __init__(self, field: str, message: str):
        """[provided]"""
        super().__init__(f"{field}: {message}")
        self.field = field


def parse_ts(value: str, field: str) -> datetime:
    """ISO-8601 (with optional Z) -> aware UTC datetime, else ValidationError."""
    try:
        dt = datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(field, f"not an ISO timestamp: {value!r}") from None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def validate_row(raw: dict, required: Iterable[str], allowed_status: Iterable[str]) -> dict:
    """Clean + type one raw row or raise ValidationError (first problem wins).

    Output: order_id, customer_id, product_id (stripped), quantity:int>=1, unit_price:float>=0,
    order_ts/updated_at: aware datetimes (updated_at must not be before order_ts),
    status (upper, allowed), channel (lower), country (upper, 2 letters), plus `_source`/`_line`.
    """
    if "_error" in raw:
        raise ValidationError("_row", raw["_error"])
    for col in required:
        if not (raw.get(col) or "").strip():
            raise ValidationError(col, "is required")
    try:
        quantity = int(raw["quantity"])
    except ValueError:
        raise ValidationError("quantity", f"not an integer: {raw['quantity']!r}") from None
    if quantity < 1:
        raise ValidationError("quantity", f"must be >= 1, got {quantity}")
    try:
        unit_price = float(raw["unit_price"])
    except ValueError:
        raise ValidationError("unit_price", f"not a number: {raw['unit_price']!r}") from None
    if unit_price < 0:
        raise ValidationError("unit_price", "must be >= 0")
    status = raw["status"].strip().upper()
    if status not in set(allowed_status):
        raise ValidationError("status", f"not allowed: {status!r}")
    order_ts = parse_ts(raw["order_ts"], "order_ts")
    updated_at = parse_ts(raw["updated_at"], "updated_at")
    if updated_at < order_ts:
        raise ValidationError("updated_at", "is before order_ts")
    country = raw["country"].strip().upper()
    if len(country) != 2 or not country.isalpha():
        raise ValidationError("country", f"not a 2-letter code: {country!r}")
    return {"order_id": raw["order_id"].strip(), "customer_id": raw["customer_id"].strip(), "product_id": raw["product_id"].strip(),
            "quantity": quantity, "unit_price": unit_price, "order_ts": order_ts, "updated_at": updated_at, "status": status,
            "channel": raw["channel"].strip().lower(), "country": country,
            "_source": raw.get("_source"), "_line": raw.get("_line")}


def transform(record: dict, customers: dict[str, dict]) -> dict:
    """Add amount (2 dp), order_date (UTC date ISO), customer_segment (or 'unknown'), is_known_customer."""
    customer = customers.get(record["customer_id"])
    return {**record, "amount": round(record["quantity"] * record["unit_price"], 2),
            "order_date": record["order_ts"].date().isoformat(),
            "customer_segment": customer.get("segment", "unknown") if customer else "unknown",
            "is_known_customer": customer is not None}


def dedupe_latest(records: Iterable[dict], key: str, version: str) -> tuple[list[dict], int]:
    """Keep the record with the greatest `version` per `key` (ties: later wins). Returns (records sorted by key, removed)."""
    best: dict = {}
    seen = 0
    for r in records:
        seen += 1
        current = best.get(r[key])
        if current is None or r[version] >= current[version]:
            best[r[key]] = r
    return [best[k] for k in sorted(best)], seen - len(best)


def daily_summary(records: Iterable[dict]) -> list[dict]:
    """Per (order_date, country, channel) excluding CANCELLED: orders, units, revenue (2 dp). Sorted by the key."""
    groups = defaultdict(lambda: {"orders": 0, "units": 0, "revenue": 0.0})
    for r in records:
        if r["status"] == "CANCELLED":
            continue
        g = groups[(r["order_date"], r["country"], r["channel"])]
        g["orders"] += 1
        g["units"] += r["quantity"]
        g["revenue"] += r["amount"]
    return [{"order_date": d, "country": c, "channel": ch, "orders": g["orders"], "units": g["units"], "revenue": round(g["revenue"], 2)}
            for (d, c, ch), g in sorted(groups.items())]


def customer_summary(records: Iterable[dict]) -> list[dict]:
    """Per customer excluding CANCELLED: orders, revenue (2 dp), first_order, last_order (dates), segment. Sorted by revenue desc, id."""
    groups: dict[str, dict] = {}
    for r in records:
        if r["status"] == "CANCELLED":
            continue
        g = groups.setdefault(r["customer_id"], {"customer_id": r["customer_id"], "segment": r["customer_segment"], "orders": 0,
                                                  "revenue": 0.0, "first_order": r["order_date"], "last_order": r["order_date"]})
        g["orders"] += 1
        g["revenue"] += r["amount"]
        g["first_order"] = min(g["first_order"], r["order_date"])
        g["last_order"] = max(g["last_order"], r["order_date"])
    for g in groups.values():
        g["revenue"] = round(g["revenue"], 2)
    return sorted(groups.values(), key=lambda g: (-g["revenue"], g["customer_id"]))
