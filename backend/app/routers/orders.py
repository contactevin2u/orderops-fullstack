from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel
from ..db import get_session
from ..models import Order, OrderItem, Plan, Customer
from ..schemas import OrderOut
from ..services.ordersvc import create_order_from_parsed

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=list[OrderListOut])
def list_orders(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_session)):
    rows = db.query(Order, Customer).join(Customer, Customer.id==Order.customer_id).order_by(Order.id.desc()).limit(limit).all()
    out = []
    for o,c in rows:
        out.append(OrderListOut.model_validate({
            "id": o.id, "code": o.code, "type": o.type, "status": o.status, "subtotal": float(o.subtotal), "total": float(o.total),
            "paid_amount": float(o.paid_amount), "balance": float(o.balance), "customer_name": c.name
        }))
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
    if not order: raise HTTPException(404, "Not found")
    return OrderOut.model_validate(order)

class CancelInstallmentIn(BaseModel):
    penalty_fee: float = 0
    return_delivery_fee: float = 0
    reason: str | None = None

@router.post("/{order_id}/cancel-installment", response_model=OrderOut)
def cancel_installment(order_id: int, body: CancelInstallmentIn, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order: raise HTTPException(404, "Not found")
    if order.type != "INSTALLMENT": raise HTTPException(400, "Not an installment order")
    order.status = "CANCELLED"
    order.penalty_fee = (order.penalty_fee or 0) + (body.penalty_fee or 0)
    order.return_delivery_fee = (order.return_delivery_fee or 0) + (body.return_delivery_fee or 0)
    order.total = (order.subtotal or 0) - (order.discount or 0) + (order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0)
    order.balance = order.total - (order.paid_amount or 0)
    db.commit(); db.refresh(order)
    return OrderOut.model_validate(order)

class BuybackIn(BaseModel):
    buyback_amount: float = 0
    return_delivery_fee: float = 0
    note: str | None = None

@router.post("/{order_id}/buyback", response_model=OrderOut)
def buyback(order_id: int, body: BuybackIn, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order: raise HTTPException(404, "Not found")
    # apply negative amount as discount + add return fee
    order.discount = (order.discount or 0) + float(body.buyback_amount or 0)
    order.return_delivery_fee = (order.return_delivery_fee or 0) + (body.return_delivery_fee or 0)
    order.total = (order.subtotal or 0) - (order.discount or 0) + (order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0)
    order.balance = order.total - (order.paid_amount or 0)
    db.commit(); db.refresh(order)
    return OrderOut.model_validate(order)
