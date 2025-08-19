from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from decimal import Decimal, InvalidOperation
from datetime import datetime

from ..models import Customer, Order, OrderItem, Plan

NUM0 = Decimal("0.00")

def _D(x) -> Decimal:
    if x is None:
        return NUM0
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x).strip().replace(",", ""))
    except (InvalidOperation, AttributeError):
        return NUM0

def _unique_code(db: Session, desired: str | None) -> str:
    base = (desired or "").strip().upper()
    if not base:
        base = f"TMP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    code = base
    # Ensure uniqueness by suffixing -2, -3, ...
    i = 2
    while db.execute(select(Order.id).where(Order.code == code)).first():
        code = f"{base}-{i}"
        i += 1
    return code

def _get_or_create_customer(db: Session, name: str, phone: str, address: str) -> Customer:
    q = db.execute(
        select(Customer).where(
            func.replace(func.replace(Customer.phone, " ", ""), "-", "") ==
            func.replace(func.replace(phone or "", " ", ""), "-", "")
        )
    ).scalar_one_or_none()
    if q:
        # update sparse fields if missing
        updated = False
        if (name or "").strip() and q.name != name:
            q.name = name.strip(); updated = True
        if (address or "").strip() and q.address != address:
            q.address = address.strip(); updated = True
        if updated:
            db.add(q)
        return q
    c = Customer(
        name=(name or "").strip() or "Unknown",
        phone=(phone or "").strip(),
        address=(address or "").strip(),
    )
    db.add(c)
    db.flush()
    return c

def _compute_totals(order_type: str, items: list[dict], charges: dict, plan: dict, totals: dict) -> tuple[Decimal, Decimal]:
    """
    Returns (total_due_today, one_time_subtotal)
    """
    delivery_fee = _D(charges.get("delivery_fee"))
    return_delivery_fee = _D(charges.get("return_delivery_fee"))
    penalty_fee = _D(charges.get("penalty_fee"))
    discount = _D(charges.get("discount"))

    # OUTRIGHT items contribute to one-time subtotal
    one_time_subtotal = NUM0
    for it in items:
        it_type = (it.get("item_type") or "").upper()
        qty = int(it.get("qty") or 1)
        if it_type == "OUTRIGHT":
            one_time_subtotal += _D(it.get("unit_price")) * qty

    # Initial recurring for INSTALLMENT/RENTAL is the first month
    initial_recurring = NUM0
    if order_type in ("INSTALLMENT", "RENTAL"):
        # Prefer plan.monthly_amount
        initial_recurring = _D(plan.get("monthly_amount"))
        # Fallback: any item monthly_amount (max)
        if initial_recurring == NUM0:
            for it in items:
                initial_recurring = max(initial_recurring, _D(it.get("monthly_amount")))

    total_due_today = (
        one_time_subtotal
        + delivery_fee
        + return_delivery_fee
        + penalty_fee
        + initial_recurring
        - discount
    )
    # If the parser provided a confident 'total', prefer it if > 0
    provided_total = _D((totals or {}).get("total"))
    if provided_total > NUM0 and abs(provided_total - total_due_today) <= _D("0.05"):
        # within 5 sen -> trust either; keep computed
        pass
    elif provided_total > NUM0 and initial_recurring == NUM0 and one_time_subtotal == NUM0:
        # in badly parsed cases, accept provided total
        total_due_today = provided_total

    return total_due_today, one_time_subtotal

def create_from_parsed(db: Session, parsed: dict) -> Order:
    cust = (parsed or {}).get("customer") or {}
    order_in = (parsed or {}).get("order") or {}

    # customer
    customer = _get_or_create_customer(
        db=db,
        name=cust.get("name") or "",
        phone=cust.get("phone") or "",
        address=cust.get("address") or "",
    )

    # core order fields
    otype = (order_in.get("type") or "OUTRIGHT").upper()
    code = _unique_code(db, order_in.get("code"))
    delivery_date = order_in.get("delivery_date")  # already ISO date or free text

    charges = order_in.get("charges") or {}
    totals = order_in.get("totals") or {}
    plan_in = order_in.get("plan") or {}
    items_in = order_in.get("items") or []

    total_due_today, one_time_subtotal = _compute_totals(otype, items_in, charges, plan_in, totals)

    paid_amount = _D(totals.get("paid"))
    balance = (total_due_today - paid_amount)

    o = Order(
        code=code,
        type=otype,
        status="NEW",  # will be updated by your lifecycle actions
        customer_id=customer.id,
        delivery_date=delivery_date,
        notes=(order_in.get("notes") or "").strip(),
        subtotal=one_time_subtotal,
        discount=_D(charges.get("discount")),
        delivery_fee=_D(charges.get("delivery_fee")),
        return_delivery_fee=_D(charges.get("return_delivery_fee")),
        penalty_fee=_D(charges.get("penalty_fee")),
        total=total_due_today,
        paid_amount=paid_amount,
        balance=balance,
    )
    db.add(o)
    db.flush()

    # Items
    for it in items_in:
        name = (it.get("name") or "Item").strip()
        qty = int(it.get("qty") or 1)
        item_type = (it.get("item_type") or otype).upper()
        unit_price = _D(it.get("unit_price"))
        line_total = _D(it.get("line_total"))
        monthly_amount = _D(it.get("monthly_amount"))

        if line_total == NUM0 and unit_price > NUM0:
            line_total = unit_price * qty
        if item_type in ("INSTALLMENT", "RENTAL") and monthly_amount == NUM0 and unit_price > NUM0:
            monthly_amount = unit_price

        oi = OrderItem(
            order_id=o.id,
            name=name,
            sku=(it.get("sku") or None),
            item_type=item_type,
            qty=qty,
            unit_price=unit_price,
            line_total=line_total,
            category=(it.get("category") or None),
            monthly_amount=monthly_amount if monthly_amount > NUM0 else None,
        )
        db.add(oi)

    # Plan (for recurring types)
    if otype in ("INSTALLMENT", "RENTAL"):
        months = int(plan_in.get("months") or (0 if otype == "RENTAL" else 1))
        monthly_amount = _D(plan_in.get("monthly_amount"))
        pl = Plan(
            order_id=o.id,
            plan_type=otype,
            months=None if otype == "RENTAL" else months,
            monthly_amount=monthly_amount if monthly_amount > NUM0 else None,
            start_date=order_in.get("delivery_date"),
        )
        db.add(pl)

    db.commit()
    db.refresh(o)
    return o
