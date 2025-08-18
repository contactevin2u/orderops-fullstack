from __future__ import annotations

from datetime import datetime, date, time
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import Customer, Order, OrderItem, Plan, Payment
from ..utils.codegen import generate_order_code

TWO_DP = Decimal("0.01")

def d(x) -> Decimal:
    if isinstance(x, Decimal):
        return x.quantize(TWO_DP, rounding=ROUND_HALF_UP)
    if x is None:
        return Decimal("0.00")
    try:
        return Decimal(str(x)).quantize(TWO_DP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")

def _unique_temp_code(db: Session) -> str:
    base = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
    attempt = base
    i = 2
    while db.execute(select(Order.id).where(Order.code == attempt)).first():
        attempt = f"{base}-{i}"
        i += 1
    return attempt

def _parse_delivery_dt(s: str | None):
    if not s:
        return None
    try:
        # try ISO first (YYYY-MM-DD or with time)
        dt = datetime.fromisoformat(s)
        return dt
    except Exception:
        # fallback: if just a date-like 'YYYY-MM-DD'
        try:
            y, m, d_ = s[:4], s[5:7], s[8:10]
            dt = datetime(int(y), int(m), int(d_), 0, 0, 0)
            return dt
        except Exception:
            return None

def create_order_from_parsed(db: Session, parsed: dict) -> Order:
    pdata = parsed.get("customer") or {}
    odata = parsed.get("order") or {}

    # --- upsert customer by phone if available ---
    phone = (pdata.get("phone") or "").strip()
    customer = None
    if phone:
        customer = db.execute(select(Customer).where(Customer.phone == phone)).scalar_one_or_none()
    if not customer:
        customer = Customer(
            name=pdata.get("name") or "Unknown",
            phone=phone or None,
            address=pdata.get("address") or None,
            map_url=pdata.get("map_url") or None,
        )
        db.add(customer)
        db.flush()

    # --- initial order (use unique temp code to avoid unique constraint crash) ---
    temp_code = _unique_temp_code(db)
    delivery_dt = _parse_delivery_dt(odata.get("delivery_date"))
    order = Order(
        code=temp_code,
        type=odata.get("type", "OUTRIGHT"),
        status="ACTIVE" if odata.get("type") in ("RENTAL", "INSTALLMENT") else "NEW",
        customer_id=customer.id,
        delivery_date=delivery_dt,
        notes=odata.get("notes") or None,
    )
    db.add(order)
    db.flush()  # need order.id

    # --- items ---
    items = odata.get("items") or []
    subtotal = Decimal("0.00")
    for it in items:
        qty = d(it.get("qty") or 1)
        unit_price = d(it.get("unit_price") or it.get("price") or 0)
        line_total = d(it.get("line_total") or (qty * unit_price))
        oi = OrderItem(
            order_id=order.id,
            name=it.get("name") or "Item",
            sku=it.get("sku") or None,
            category=it.get("category") or None,
            item_type=it.get("item_type") or odata.get("type") or "OUTRIGHT",
            qty=int(qty),
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(oi)
        subtotal += line_total

    # --- charges ---
    charges = odata.get("charges") or {}
    delivery_fee = d(charges.get("delivery_fee"))
    return_delivery_fee = d(charges.get("return_delivery_fee"))
    penalty_fee = d(charges.get("penalty_fee"))
    discount = d(charges.get("discount"))

    # --- totals ---
    provided_totals = odata.get("totals") or {}
    computed_total = (subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee).quantize(TWO_DP)
    total = d(provided_totals.get("total")) or computed_total
    paid = d(provided_totals.get("paid"))
    balance = (total - paid).quantize(TWO_DP)

    order.subtotal = subtotal
    order.discount = discount
    order.delivery_fee = delivery_fee
    order.return_delivery_fee = return_delivery_fee
    order.penalty_fee = penalty_fee
    order.total = total
    order.paid_amount = paid
    order.balance = balance

    # --- plan ---
    plan_data = odata.get("plan") or {}
    plan_type = plan_data.get("plan_type")
    if not plan_type and odata.get("type") in ("RENTAL", "INSTALLMENT"):
        plan_type = odata.get("type")
    if plan_type in ("RENTAL", "INSTALLMENT"):
        months = plan_data.get("months")
        monthly_amount = d(plan_data.get("monthly_amount"))
        start_d = delivery_dt.date() if delivery_dt else date.today()
        plan = Plan(
            order_id=order.id,
            plan_type=plan_type,
            months=int(months) if months is not None and str(months).isdigit() else None,
            monthly_amount=monthly_amount,
            start_date=start_d,
        )
        db.add(plan)

    # --- payment (cash-basis immediate) ---
    if paid > Decimal("0.00"):
        p = Payment(
            order_id=order.id,
            date=date.today(),
            amount=paid,
            method="cash",
            reference="intake",
            category="ORDER",
        )
        db.add(p)
