"""Validation, normalization, dedup and enrichment of API records (pure functions)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

ORDER_STATUSES = {"PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}


def _parse_ts(value) -> datetime | None:
    """ISO string (Z/offset/naive=UTC) -> aware UTC datetime, or None if unparseable."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    """[provided] Aware datetime -> 'YYYY-MM-DDTHH:MM:SSZ'."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_customer(c: dict) -> list[str]:
    """Problems with a customer record: missing customer_id/name, email without '@', bad signup_date."""
    errors = []
    if not str(c.get("customer_id") or "").strip():
        errors.append("customer_id is required")
    if not str(c.get("name") or "").strip():
        errors.append("name is required")
    email = c.get("email")
    if email and "@" not in str(email):
        errors.append("email is invalid")
    if c.get("signup_date") and _parse_ts(c["signup_date"]) is None:
        errors.append("signup_date is invalid")
    return errors


def validate_order(o: dict) -> list[str]:
    """Problems with an order record: ids, quantity (int >= 1), unit_price (number >= 0, not null), status, timestamps."""
    errors = []
    for field in ("order_id", "customer_id", "product_id"):
        if not str(o.get(field) or "").strip():
            errors.append(f"{field} is required")
    q = o.get("quantity")
    if not isinstance(q, int) or isinstance(q, bool) or q < 1:
        errors.append("quantity must be an integer >= 1")
    p = o.get("unit_price")
    if p is None or isinstance(p, bool) or not isinstance(p, (int, float)) or p < 0:
        errors.append("unit_price must be a number >= 0")
    if str(o.get("status", "")).upper() not in ORDER_STATUSES:
        errors.append("status is invalid")
    for field in ("order_ts", "updated_at"):
        if _parse_ts(o.get(field)) is None:
            errors.append(f"{field} is invalid")
    return errors


def normalize_customer(c: dict) -> dict:
    """Trim/case-normalize: name title-cased, email lowercased (None if blank), country upper, is_active bool."""
    email = str(c.get("email") or "").strip().lower()
    return {"customer_id": c["customer_id"].strip(), "name": " ".join(str(c["name"]).split()).title(),
            "email": email or None, "country": str(c.get("country") or "").strip().upper() or None,
            "segment": c.get("segment"), "signup_date": c.get("signup_date"), "is_active": bool(c.get("is_active"))}


def normalize_order(o: dict) -> dict:
    """Typed, UTC-normalized order with amount (2 dp) and order_date."""
    order_ts, updated_at = _parse_ts(o["order_ts"]), _parse_ts(o["updated_at"])
    return {"order_id": o["order_id"], "customer_id": o["customer_id"], "product_id": o["product_id"],
            "quantity": o["quantity"], "unit_price": float(o["unit_price"]), "amount": round(o["quantity"] * o["unit_price"], 2),
            "status": o["status"].upper(), "channel": str(o.get("channel") or "").lower() or None, "country": o.get("country"),
            "order_ts": iso(order_ts), "order_date": order_ts.date().isoformat(), "updated_at": iso(updated_at)}


def latest_by(records: Iterable[dict], key: str, version: str) -> tuple[list[dict], int]:
    """Keep the greatest `version` per key (ties: later wins). Returns (records sorted by key, duplicates_removed)."""
    best, seen = {}, 0
    for r in records:
        seen += 1
        if r[key] not in best or r[version] >= best[r[key]][version]:
            best[r[key]] = r
    return [best[k] for k in sorted(best)], seen - len(best)


def enrich_orders(orders: Iterable[dict], customers: dict[str, dict]) -> list[dict]:
    """Add customer_name, customer_segment (None when unknown) and customer_known flag."""
    out = []
    for o in orders:
        c = customers.get(o["customer_id"])
        out.append({**o, "customer_name": c["name"] if c else None, "customer_segment": c.get("segment") if c else None,
                    "customer_known": c is not None})
    return out
