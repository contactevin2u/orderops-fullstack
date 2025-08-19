from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, date
import re
import random

from sqlalchemy.orm import Session

from ..models import Customer, Order, OrderItem, Plan

def _d(val: Any) -> Decimal:
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"))
    try:
        return Decimal(str(val or "0")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")

def _parse_date_like(txt: Optional[str]) -> Optional[str]:
    if not txt:
        return None
    m = re.search(r"([0-3]?\d)[/.-]([01]?\d)(?:[/.-](\d{2,4}))?", str(txt))
    if not m:
        return None
    d = int(m.group(1)); mth = int(m.group(2))
    y = int(m.group(3)) if m.group(3) else datetime.utcnow().year
    if y < 100:
        y += 2000
    try:
        return date(y, mth, d).isoformat()
    except ValueError:
        return None

def _ensure_unique_code(db: Session, code: Optional[str]) -> str:
    base = (code or "").strip() or ""
    if base:
        exists = db.query(Order).filter(Order.code == base).first()
        if not exists:
            return base
    # Generate TMP-YYMMDD-HHMMSS-XXXX
    while True:
        tmp = f"TMP-{datetime.utcnow():%y%m%d-%H%M%S}-{random.randrange(1000,9999)}"
        if not db.query(Order).filter(Order.code == tmp).first():
            return tmp

def _first_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # Pick the first 9-14 digit sequence
    m = re.search(r"(\+?\d{9,14})", raw.replace("/", " "))
    return m.group(1) if m else None

def _order_to_dto(order: Order) -> Dict[str, Any]:
    return {
        "id": order.id,
        "code": order.code,
        "type": order.type,
        "status": order.status,
        "customer": {
            "id": order.customer.id if order.customer else None,
            "name": order.customer.name if order.customer else None,
            "phone": order.customer.phone if order.customer else None,
            "address": order.customer.address if order.customer else None,
        },
        "delivery_date": order.delivery_date.isoformat() if getattr(order, "delivery_date", None) else None,
        "notes": order.notes,
        "subtotal": float(order.subtotal or 0),
        "discount": float(order.discount or 0),
        "delivery_fee": float(order.delivery_fee or 0),
        "return_delivery_fee": float(order.return_delivery_fee or 0),
        "penalty_fee": float(order.penalty_fee or 0),
        "total": float(order.total or 0),
        "paid_amount": float(order.paid_amount or 0),
        "balance": float(order.balance or 0),
        "items": [
            {
                "id": it.id,
                "name": it.name,
                "sku": it.sku,
                "qty": it.qty,
                "unit_price": float(it.unit_price or 0),
                "line_total": float(it.line_total or 0),
                "category": it.category,
                "item_type": it.item_type,
            }
            for it in (order.items or [])
        ],
        "plan": {
            "id": order.plan.id if order.plan else None,
            "plan_type": order.plan.plan_type if order.plan else None,
            "months": order.plan.months if order.plan else None,
            "monthly_amount": float(order.plan.monthly_amount or 0) if order.plan else 0,
            "start_date": order.plan.start_date.isoformat() if (order.plan and order.plan.start_date) else None,
        } if order.plan else None,
        "created_at": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
        "updated_at": order.updated_at.isoformat() if getattr(order, "updated_at", None) else None,
    }

def create_order_from_parsed(db: Session, parsed: Dict[str, Any]) -> Dict[str, Any]:
    cust = (parsed or {}).get("customer") or {}
    oin = (parsed or {}).get("order") or {}
    charges = oin.get("charges") or {}
    plan_in = oin.get("plan") or {}

    # Upsert/find customer by phone (fallback by name)
    phone = _first_phone(cust.get("phone"))
    customer = None
    if phone:
        customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer:
        customer = Customer(
            name=(cust.get("name") or "").strip() or "Unknown",
            phone=phone,
            address=(cust.get("address") or "").strip() or None,
        )
        db.add(customer)
        db.flush()

    # Unique code
    code = _ensure_unique_code(db, oin.get("code"))

    # Delivery date
    delivery_iso = _parse_date_like(oin.get("delivery_date"))
    delivery_date = datetime.fromisoformat(delivery_iso) if delivery_iso else None

    # Build Order
    order = Order(
        code=code,
        type=(oin.get("type") or "OUTRIGHT").upper(),
        status="NEW",
        customer_id=customer.id,
        delivery_date=delivery_date,
        notes=(oin.get("notes") or "").strip() or None,
        subtotal=_d(oin.get("totals", {}).get("subtotal")),
        discount=_d(charges.get("discount")),
        delivery_fee=_d(charges.get("delivery_fee")),
        return_delivery_fee=_d(charges.get("return_delivery_fee")),
        penalty_fee=_d(charges.get("penalty_fee")),
        total=_d(oin.get("totals", {}).get("total")),
        paid_amount=_d(oin.get("totals", {}).get("paid")),
        balance=_d(oin.get("totals", {}).get("to_collect")),
    )
    db.add(order)
    db.flush()

    # Items
    items = oin.get("items") or []
    for it in items:
        unit_price = _d(it.get("unit_price") if it.get("unit_price") is not None else it.get("line_total"))
        qty = int(it.get("qty") or 1)
        from decimal import Decimal as _Dec
        line_total = (unit_price * qty).quantize(_Dec("0.01"))
        db.add(OrderItem(
            order_id=order.id,
            name=(it.get("name") or "").strip(),
            sku=(it.get("sku") or None),
            qty=qty,
            unit_price=unit_price,
            line_total=line_total,
            category=(it.get("category") or None),
            item_type=(it.get("item_type") or order.type),
        ))

    # Plan (only for RENTAL / INSTALLMENT)
    if order.type in ("RENTAL", "INSTALLMENT"):
        monthly_amount = _d(plan_in.get("monthly_amount") or oin.get("totals", {}).get("monthly_amount"))
        months = plan_in.get("months")
        plan = Plan(
            order_id=order.id,
            plan_type=order.type,
            months=int(months) if months else None,
            monthly_amount=monthly_amount,
            start_date=datetime.fromisoformat(plan_in["start_date"]) if plan_in.get("start_date") else delivery_date,
        )
        db.add(plan)

    # If totals missing, recompute conservatively
    if order.total == Decimal("0.00"):
        sum_items = sum((i.line_total for i in order.items), Decimal("0.00"))
        order.subtotal = sum_items
        order.total = (sum_items + order.delivery_fee + order.return_delivery_fee + order.penalty_fee - order.discount).quantize(Decimal("0.01"))
        order.balance = (order.total - order.paid_amount).quantize(Decimal("0.01"))

    db.commit()
    db.refresh(order)
    return _order_to_dto(order)
