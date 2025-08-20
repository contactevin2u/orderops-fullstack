from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date

from ..db import get_session
from ..models import Order, OrderItem, Plan, Customer
from ..schemas import OrderOut
from ..services.ordersvc import create_order_from_parsed
from ..services.plan_math import calculate_plan_due

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=list[OrderListOut])
def list_orders(
    q: str | None = None,
    status: str | None = None,
    type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
):
    stmt = select(Order, Customer.name.label("customer_name")).join(
        Customer, Customer.id == Order.customer_id
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Order.code.ilike(like), Customer.name.ilike(like)))
    if status:
        stmt = stmt.where(Order.status == status)
    if type:
        stmt = stmt.where(Order.type == type)
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    out: list[OrderListOut] = []
    for (order, customer_name) in rows:
        dto = OrderOut.model_validate(order).model_dump()
        dto["customer_name"] = customer_name
        out.append(OrderListOut.model_validate(dto))
    return out

class ManualOrderIn(BaseModel):
    customer: dict
    order: dict

@router.post("", response_model=OrderOut, status_code=201)
def create_order(body: ManualOrderIn, db: Session = Depends(get_session)):
    try:
        order = create_order_from_parsed(db, {"customer": body.customer, "order": body.order})
        return OrderOut.model_validate(order)
    except Exception as e:
        raise HTTPException(400, f"Create failed: {e}")

@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return OrderOut.model_validate(order)


@router.get("/{order_id}/due", response_model=dict)
def get_order_due(order_id: int, as_of: date | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    as_of = as_of or date.today()
    plan = order.plan
    if order.type in ("INSTALLMENT", "RENTAL") and plan:
        expected = calculate_plan_due(plan, as_of)
    else:
        expected = Decimal("0.00")

    paid = order.paid_amount or Decimal("0.00")
    add_fees = (order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0)
    balance = (expected + Decimal(str(add_fees)) - paid).quantize(Decimal("0.01"))

    return {
        "expected": float(expected),
        "paid": float(paid),
        "balance": float(balance),
    }

@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: int, body: dict, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    for k in ["notes", "status", "delivery_date"]:
        if k in body and body[k] is not None:
            setattr(order, k, body[k])

    money_fields = [
        "subtotal",
        "discount",
        "delivery_fee",
        "return_delivery_fee",
        "penalty_fee",
        "total",
        "balance",
    ]
    for k in money_fields:
        if k in body and body[k] is not None:
            setattr(order, k, Decimal(str(body[k])))

    # Optional plan update
    if "plan" in body and order.plan:
        plan_patch = body.get("plan") or {}
        for k in ["plan_type", "months", "monthly_amount", "status"]:
            if k in plan_patch and plan_patch[k] is not None:
                setattr(order.plan, k, plan_patch[k])
        if plan_patch.get("start_date"):
            try:
                order.plan.start_date = datetime.fromisoformat(plan_patch["start_date"]).date()
            except Exception:
                pass

    # Optional items update
    if "items" in body:
        items_patch = body.get("items") or []
        for ip in items_patch:
            iid = ip.get("id")
            if not iid:
                continue
            item = next((it for it in order.items if it.id == iid), None)
            if not item:
                continue
            for k in ["name", "item_type", "sku", "category"]:
                if k in ip and ip[k] is not None:
                    setattr(item, k, ip[k])
            if "qty" in ip and ip["qty"] is not None:
                item.qty = int(ip["qty"])
            for k in ["unit_price", "line_total"]:
                if k in ip and ip[k] is not None:
                    setattr(item, k, Decimal(str(ip[k])))

        # Recompute subtotal and totals when items change
        subtotal = sum((itm.line_total or (itm.unit_price * itm.qty)) for itm in order.items)
        order.subtotal = subtotal
        order.total = subtotal - order.discount + order.delivery_fee + order.return_delivery_fee + order.penalty_fee
        order.balance = order.total - order.paid_amount

    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)

@router.post("/{order_id}/void", response_model=dict)
def void_order(order_id: int, body: dict | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    reason = (body or {}).get("reason") if body else None
    order.status = "CANCELLED"
    if hasattr(order, "notes") and reason:
        order.notes = (order.notes or "") + f"\n[VOID] {reason}"

    # If no posted payments, zero out totals
    paid_total = sum([p.amount for p in order.payments if getattr(p, "status", "POSTED") == "POSTED"], Decimal("0.00"))
    if paid_total == Decimal("0"):
        order.total = Decimal("0.00")
        order.balance = Decimal("0.00")

    db.commit()
    db.refresh(order)
    return {"ok": True, "order_id": order.id, "status": order.status}


class ReturnIn(BaseModel):
    date: str | None = None


@router.post("/{order_id}/return", response_model=OrderOut)
def return_order(order_id: int, body: ReturnIn | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    # Optional return date – reuse delivery_date field
    if body and body.date:
        try:
            order.delivery_date = datetime.fromisoformat(body.date)
        except Exception:
            pass

    order.status = "RETURNED"

    total = (order.subtotal - order.discount + order.delivery_fee + order.return_delivery_fee + order.penalty_fee)
    order.total = total
    order.balance = total - order.paid_amount

    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


class BuybackIn(BaseModel):
    amount: float


@router.post("/{order_id}/buyback", response_model=OrderOut)
def buyback_order(order_id: int, body: BuybackIn, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.type != "OUTRIGHT":
        raise HTTPException(400, "Buyback only allowed for OUTRIGHT orders")

    amt = Decimal(str(body.amount))
    if amt <= Decimal("0"):
        raise HTTPException(400, "Invalid buyback amount")

    order.discount += amt
    order.status = "RETURNED"

    total = (order.subtotal - order.discount + order.delivery_fee + order.return_delivery_fee + order.penalty_fee)
    order.total = total
    order.balance = total - order.paid_amount

    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)
