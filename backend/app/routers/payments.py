from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from ..db import get_session
from ..models import Payment, Order

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentIn(BaseModel):
    order_id: int
    amount: float
    date: str | None = None
    method: str | None = None
    reference: str | None = None
    category: str | None = "ORDER"

@router.post("", response_model=dict, status_code=201)
def add_payment(body: PaymentIn, db: Session = Depends(get_session)):
    order = db.get(Order, body.order_id)
    if not order: raise HTTPException(404, "Order not found")
    pdate = date.fromisoformat(body.date) if body.date else date.today()
    p = Payment(order_id=order.id, amount=body.amount, date=pdate, method=body.method, reference=body.reference, category=body.category or "ORDER")
    db.add(p)
    order.paid_amount = (order.paid_amount or 0) + float(body.amount or 0)
    order.balance = (order.total or 0) - (order.paid_amount or 0)
    db.commit(); db.refresh(order)
    return {"payment_id": p.id, "order_balance": float(order.balance)}

class VoidIn(BaseModel):
    reason: str | None = None

@router.post("/{payment_id}/void", response_model=dict)
def void_payment(payment_id: int, body: VoidIn, db: Session = Depends(get_session)):
    p = db.get(Payment, payment_id)
    if not p: raise HTTPException(404, "Payment not found")
    if p.status == "VOIDED": return {"ok": True, "status": "VOIDED"}
    p.status = "VOIDED"; p.void_reason = body.reason or ""
    order = db.get(Order, p.order_id)
    order.paid_amount = (order.paid_amount or 0) - float(p.amount or 0)
    order.balance = (order.total or 0) - (order.paid_amount or 0)
    db.commit(); db.refresh(order)
    return {"ok": True, "status": "VOIDED", "order_balance": float(order.balance)}
