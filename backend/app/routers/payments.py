from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, condecimal
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from ..db import get_session
from ..models import Payment, Order

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentIn(BaseModel):
    order_id: int
    amount: condecimal(max_digits=12, decimal_places=2)
    date: str | None = None
    method: str | None = None
    reference: str | None = None
    category: str | None = "ORDER"

class VoidIn(BaseModel):
    reason: str | None = None

TWO_DP = Decimal("0.01")

def to_decimal(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    if x is None:
        return Decimal("0")
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return Decimal("0")

def q2(x) -> Decimal:
    return to_decimal(x).quantize(TWO_DP, rounding=ROUND_HALF_UP)

@router.post("", response_model=dict, status_code=201)
def add_payment(body: PaymentIn, db: Session = Depends(get_session)):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        pdate = date.fromisoformat(body.date) if body.date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD")

    amt = q2(body.amount)
    if amt <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Amount must be > 0")

    payment = Payment(
        order_id=order.id,
        amount=amt,
        date=pdate,
        method=body.method,
        reference=body.reference,
        category=body.category or "ORDER",
    )
    db.add(payment)
    db.flush()

    current_paid = to_decimal(order.paid_amount)
    new_paid = q2(current_paid + amt)
    order_total = to_decimal(order.total)
    new_balance = q2(order_total - new_paid)

    order.paid_amount = new_paid
    order.balance = new_balance
    db.commit()
    db.refresh(order)

    return {
        "ok": True,
        "payment_id": payment.id,
        "order_id": order.id,
        "order_paid_amount": str(order.paid_amount),
        "order_balance": str(order.balance),
    }

@router.post("/{payment_id}/void", response_model=dict)
def void_payment(payment_id: int, body: VoidIn, db: Session = Depends(get_session)):
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")

    if getattr(p, "status", "") == "VOIDED":
        order = db.get(Order, p.order_id)
        return {
            "ok": True,
            "status": "VOIDED",
            "order_id": p.order_id,
            "order_paid_amount": str(order.paid_amount if order else Decimal("0.00")),
            "order_balance": str(order.balance if order else Decimal("0.00")),
        }

    p.status = "VOIDED"
    p.void_reason = (body.reason or "").strip()

    order = db.get(Order, p.order_id)
    if order:
        current_paid = to_decimal(order.paid_amount)
        amt = to_decimal(p.amount)
        new_paid = q2(current_paid - amt)
        if new_paid < Decimal("0"):
            new_paid = Decimal("0.00")
        order_total = to_decimal(order.total)
        new_balance = q2(order_total - new_paid)
        order.paid_amount = new_paid
        order.balance = new_balance

    db.commit()
    if order:
        db.refresh(order)

    return {
        "ok": True,
        "status": "VOIDED",
        "payment_id": p.id,
        "order_id": p.order_id,
        "order_paid_amount": str(order.paid_amount if order else Decimal("0.00")),
        "order_balance": str(order.balance if order else Decimal("0.00")),
    }
