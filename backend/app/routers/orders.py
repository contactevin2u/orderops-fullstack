from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel
from decimal import Decimal

from ..db import get_session
from ..models import Order, OrderItem, Plan, Customer
from ..schemas import OrderOut
from ..services.ordersvc import create_order_from_parsed

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=list[OrderListOut])
def list_orders(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_session)):
    stmt = (
        select(Order, Customer.name.label("customer_name"))
        .join(Customer, Customer.id == Order.customer_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
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

@router.put("/{order_id}", response_model=dict)
def update_order(order_id: int, body: dict, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    for k in ["notes", "status"]:
        if k in body:
            setattr(order, k, body[k])

    money_fields = [
        "subtotal", "discount", "delivery_fee",
        "return_delivery_fee", "penalty_fee",
        "total", "balance"
    ]
    for k in money_fields:
        if k in body and body[k] is not None:
            setattr(order, k, Decimal(str(body[k])))

    db.commit()
    db.refresh(order)
    return {"ok": True, "order_id": order.id}

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
