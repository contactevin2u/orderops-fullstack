from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
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

CENT = Decimal("0.01")
DEC0 = Decimal("0.00")


def q2(value: Decimal) -> Decimal:
    return (value or Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


PLAN_ITEM_TYPES = {"RENTAL", "INSTALLMENT"}
FEE_ITEM_TYPES = {"FEE"}




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


def _compute_subtotal_from_items(items) -> Decimal:
    """Simple subtotal: sum all line_total values"""
    subtotal = Decimal("0")
    for it in items or []:
        if isinstance(it, dict):
            lt = it.get("line_total")
        else:
            lt = getattr(it, "line_total", None)
        subtotal += Decimal(str(lt or 0))
    return q2(subtotal)


def _sum_posted_payments(order) -> Decimal:
    total = Decimal("0")
    for p in getattr(order, "payments", []) or []:
        if getattr(p, "status", None) == "POSTED":
            total += Decimal(str(p.amount))
    return q2(total)


# Deleted complex first month fee logic


def _apply_charges_and_totals(
    items: list[dict],
    charges: dict | None,
    totals: dict | None,
) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Simple calculation"""
    charges = charges or {}
    totals = totals or {}
    
    subtotal = _compute_subtotal_from_items(items)
    discount = to_decimal(charges.get("discount"))
    delivery_fee = to_decimal(charges.get("delivery_fee"))
    return_delivery_fee = to_decimal(charges.get("return_delivery_fee"))
    penalty_fee = to_decimal(charges.get("penalty_fee"))
    
    total = subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee
    paid = to_decimal(totals.get("paid"))
    
    return (q2(subtotal), q2(discount), q2(delivery_fee), q2(return_delivery_fee), q2(penalty_fee), q2(total), q2(paid))


CONST_CANCEL_SUFFIX = "-C"
CONST_RETURN_SUFFIX = "-R"
CONST_BUYBACK_SUFFIX = "-B"


# -------------------------------
# Public API
# -------------------------------

def create_adjustment_order(
    db: Session,
    parent: Order,
    suffix: str,
    lines: list[dict],
    charges: dict,
) -> Order:
    """Create a child adjustment order linked to ``parent``."""
    raw_code = f"{parent.code}{suffix}"
    code = _ensure_unique_code(db, raw_code)
    subtotal, discount, df, rdf, pf, total, paid = _apply_charges_and_totals(lines, charges, None)
    balance = q2(total - paid)

    adj = Order(
        code=code,
        type=parent.type,
        status=parent.status,
        customer_id=parent.customer_id,
        parent_id=parent.id,
        delivery_date=parent.delivery_date,
        notes=None,
        subtotal=subtotal,
        discount=discount,
        delivery_fee=df,
        return_delivery_fee=rdf,
        penalty_fee=pf,
        total=total,
        paid_amount=paid,
        balance=balance,
    )
    db.add(adj)
    db.flush()

    for it in lines:
        name = (it.get("name") or "").strip() or "Item"
        item_type = (it.get("item_type") or parent.type).strip().upper()
        qty = to_decimal(it.get("qty") or 1)
        unit_price = to_decimal(it.get("unit_price"))
        line_total = to_decimal(it.get("line_total"))
        if item_type in PLAN_ITEM_TYPES:
            if unit_price <= 0 and line_total <= 0:
                unit_price = DEC0
                line_total = DEC0

        db.add(
            OrderItem(
                order_id=adj.id,
                name=name,
                sku=it.get("sku"),
                category=it.get("category"),
                item_type=item_type,
                qty=int(qty),
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    return adj


def recompute_financials(order: Order) -> None:
    """Simple recompute"""
    paid = _sum_posted_payments(order)
    order.paid_amount = paid
    order.balance = q2((order.total or DEC0) - paid)


def ensure_plan_first_month_fee(order: Order) -> None:
    """Skip complex fee logic"""
    pass

def create_from_parsed(db: Session, payload: Dict[str, Any], idempotency_key: str | None = None) -> Order:
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

    # Simple plan creation aligned with business logic
    plan_in = order_data.get("plan") or {}
    should_create_plan = otype in ("INSTALLMENT", "RENTAL") or plan_in
    
    # Plan type: INSTALLMENT (RM159 x 6), RENTAL (RM240/bulan), or infer from items  
    plan_type = otype if otype in ("INSTALLMENT", "RENTAL") else "RENTAL"
    
    # For INSTALLMENT: months is required (e.g., 6 months)
    # For RENTAL: months is None (unlimited until return)
    months = plan_in.get("months") if plan_type == "INSTALLMENT" else None
    
    # Monthly amount from plan or aggregate from items with monthly_amount
    monthly_amount = to_decimal(plan_in.get("monthly_amount"))
    if monthly_amount <= 0:
        # Simple aggregation from items
        for it in items:
            ma = to_decimal(it.get("monthly_amount"))
            if ma > 0:
                monthly_amount += ma
    
    start_date = delivery_date

    subtotal, discount, df, rdf, pf, total, paid = _apply_charges_and_totals(items, charges, totals)
    balance = q2(total - paid)

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
        idempotency_key=idempotency_key,
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

        # Simplified item creation

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
    if should_create_plan:
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
