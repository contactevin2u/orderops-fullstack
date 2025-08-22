from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
import secrets
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from ..models import Customer, Order, OrderItem, Plan  # models/__init__.py exports these
from ..utils.dates import parse_relaxed_date
from ..utils.normalize import to_decimal


# -------------------------------
# Helpers
# -------------------------------

DEC0 = Decimal("0.00")




def _unique_temp_code(db: Session, prefix: str = "TMP") -> str:
    """Generate a unique temporary order code."""
    for _ in range(20):
        candidate = f"{prefix}{datetime.utcnow():%y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"
        exists = db.execute(select(Order.id).where(Order.code == candidate)).first()
        if not exists:
            return candidate
    # Extremely unlikely; last resort
    return f"{prefix}{datetime.utcnow():%y%m%d%H%M%S}-{secrets.token_hex(3).upper()}"


def _ensure_unique_code(db: Session, desired: Optional[str]) -> str:
    """
    Ensure a usable, unique code. If desired is falsy, create a temp.
    If desired exists, append a suffix -2, -3, ... until unique.
    """
    code = (desired or "").strip().upper()
    if not code:
        return _unique_temp_code(db)

    exists = db.execute(select(Order.id).where(Order.code == code)).first()
    if not exists:
        return code

    # collision: try with numeric suffixes
    base = code
    for i in range(2, 50):
        candidate = f"{base}-{i}"
        exists = db.execute(select(Order.id).where(Order.code == candidate)).first()
        if not exists:
            return candidate

    # fallback to temp if too many collisions
    return _unique_temp_code(db)


def _get_or_create_customer(db: Session, data: Dict[str, Any]) -> Customer:
    name = (data.get("name") or "").strip() or "Unknown"
    phone = (data.get("phone") or "").strip() or None
    address = (data.get("address") or "").strip() or None
    map_url = (data.get("map_url") or "").strip() or None

    cust: Optional[Customer] = None
    if phone:
        cust = db.query(Customer).filter(Customer.phone == phone).one_or_none()

    if cust:
        # Update lightweight fields if we learned more info
        updated = False
        if not cust.name and name:
            cust.name = name
            updated = True
        if not cust.address and address:
            cust.address = address
            updated = True
        if not cust.map_url and map_url:
            cust.map_url = map_url
            updated = True
        if updated:
            db.add(cust)
        return cust

    # Create new
    cust = Customer(name=name, phone=phone, address=address, map_url=map_url)
    db.add(cust)
    db.flush()  # get cust.id
    return cust


def _compute_subtotal_from_items(items: list[dict]) -> Decimal:
    subtotal = DEC0
    for it in items:
        lt = to_decimal(it.get("line_total"))
        up = to_decimal(it.get("unit_price"))
        qty = to_decimal(it.get("qty") or 1)
        monthly = to_decimal(it.get("monthly_amount"))
        # For RENTAL/INSTALLMENT items, monthly amounts should not inflate outright subtotal
        # Only include explicit unit/line totals
        if lt > 0:
            subtotal += lt
        elif up > 0:
            subtotal += (up * qty)
        # else: keep as 0.00
        # monthly is handled by Plan, not subtotal
    return subtotal


def _apply_charges_and_totals(
    items: list[dict],
    charges: dict | None,
    totals: dict | None,
) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """
    Return (subtotal, discount, delivery_fee, return_delivery_fee, penalty_fee, total, paid)
    using items + charges + totals with sane fallbacks.
    """
    charges = charges or {}
    totals = totals or {}

    subtotal = _compute_subtotal_from_items(items)
    discount = to_decimal(charges.get("discount"))
    delivery_fee = to_decimal(charges.get("delivery_fee"))
    return_delivery_fee = to_decimal(charges.get("return_delivery_fee"))
    penalty_fee = to_decimal(charges.get("penalty_fee"))

    # Primary formula if totals.total not trustworthy:
    computed_total = subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee

    total_from_payload = to_decimal(totals.get("total"))
    total = total_from_payload if total_from_payload > 0 else computed_total

    paid = to_decimal(totals.get("paid"))
    return (subtotal, discount, delivery_fee, return_delivery_fee, penalty_fee, total, paid)


# -------------------------------
# Public API
# -------------------------------

def create_from_parsed(db: Session, payload: Dict[str, Any]) -> Order:
    """
    Create an Order (plus items/plan) from a parsed payload like:

    {
      "customer": {...},
      "order": {
        "type": "OUTRIGHT|INSTALLMENT|RENTAL|MIXED",
        "code": "KP2017",
        "delivery_date": "19/8",
        "notes": "...",
        "items": [...],
        "charges": {...},
        "plan": {...},     # can be {} or None
        "totals": {...}
      }
    }
    """
    if not payload or "order" not in payload:
        raise ValueError("Invalid payload: missing 'order'")

    customer_data = payload.get("customer") or {}
    order_data = payload.get("order") or {}

    # customer
    customer = _get_or_create_customer(db, customer_data)

    # order basics
    desired_code = order_data.get("code")
    code = _ensure_unique_code(db, desired_code)

    otype = (order_data.get("type") or "OUTRIGHT").strip().upper()
    if otype not in ("OUTRIGHT", "INSTALLMENT", "RENTAL", "MIXED"):
        otype = "OUTRIGHT"

    delivery_date = parse_relaxed_date(order_data.get("delivery_date") or "")
    notes = (order_data.get("notes") or "").strip() or None

    # money fields
    items = order_data.get("items") or []
    charges = order_data.get("charges") or {}
    totals = order_data.get("totals") or {}

    subtotal, discount, df, rdf, pf, total, paid = _apply_charges_and_totals(items, charges, totals)
    balance = (total - paid).quantize(Decimal("0.01"))

    order = Order(
        code=code,
        type=otype,
        status="NEW",
        customer_id=customer.id,
        delivery_date=delivery_date,
        notes=notes,
        subtotal=subtotal,
        discount=discount,
        delivery_fee=df,
        return_delivery_fee=rdf,
        penalty_fee=pf,
        total=total,
        paid_amount=paid,
        balance=balance,
    )
    db.add(order)
    db.flush()  # get order.id

    # items
    for it in items:
        name = (it.get("name") or "").strip() or "Item"
        sku = (it.get("sku") or it.get("code") or None)
        category = (it.get("category") or None)
        item_type = (it.get("item_type") or otype).strip().upper()
        qty = to_decimal(it.get("qty") or 1)
        unit_price = to_decimal(it.get("unit_price"))
        line_total = to_decimal(it.get("line_total"))
        monthly_amount = to_decimal(it.get("monthly_amount"))

        # For rental/installment items, monthly amount is carried by Plan; keep monetary 0 at item level
        if item_type in ("RENTAL", "INSTALLMENT"):
            if unit_price <= 0 and line_total <= 0:
                unit_price = DEC0
                line_total = DEC0

        db.add(
            OrderItem(
                order_id=order.id,
                name=name,
                sku=sku,
                category=category,
                item_type=item_type,
                qty=int(qty),
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    # plan (optional)
    plan_in = order_data.get("plan") or {}
    has_plan_data = any(k in plan_in for k in ("plan_type", "months", "monthly_amount", "start_date"))
    should_create_plan = (
        otype in ("INSTALLMENT", "RENTAL")
        or has_plan_data
        or any((it.get("item_type") or "").strip().upper() in ("INSTALLMENT", "RENTAL") for it in items)
    )

    if should_create_plan:
        plan_type = (plan_in.get("plan_type") or otype).strip().upper()
        if plan_type not in ("INSTALLMENT", "RENTAL"):
            for it in items:
                itype = (it.get("item_type") or "").strip().upper()
                if itype in ("INSTALLMENT", "RENTAL"):
                    plan_type = itype
                    break
            if plan_type not in ("INSTALLMENT", "RENTAL"):
                plan_type = "RENTAL"
        months_raw = plan_in.get("months")
        months = (
            int(months_raw)
            if isinstance(months_raw, (int, float, str)) and str(months_raw).strip().isdigit()
            else None
        )

        monthly_amount = to_decimal(plan_in.get("monthly_amount"))
        # As a fallback, if not present and single-item monthly was parsed, try to infer the max monthly amount
        if monthly_amount <= 0:
            # Look for the largest 'monthly_amount' among items
            monthly_candidates = [to_decimal(it.get("monthly_amount")) for it in items if it.get("monthly_amount") is not None]
            if monthly_candidates:
                monthly_amount = max(monthly_candidates)

        start_date = parse_relaxed_date(plan_in.get("start_date") or "") or delivery_date

        db.add(
            Plan(
                order_id=order.id,
                plan_type=plan_type,
                start_date=start_date,
                months=months,
                monthly_amount=monthly_amount,
                status="ACTIVE",
            )
        )

    # finalize
    try:
        db.commit()
    except IntegrityError as ie:
        db.rollback()
        # Retry once with a unique temp code if code collision (or other unique issues)
        if "orders_code_key" in str(ie.orig) or "ix_orders_code" in str(ie.orig):
            order.code = _unique_temp_code(db)
            db.add(order)
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
        else:
            raise

    db.refresh(order)
    return order


# Backwards-compatibility export used by routers/orders.py
def create_order_from_parsed(db: Session, payload: Dict[str, Any]) -> Order:
    """Compatibility wrapper to keep older imports working."""
    return create_from_parsed(db, payload)
