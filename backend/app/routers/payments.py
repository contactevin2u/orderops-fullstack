from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Payment, Order, Role, User
from ..utils.normalize import to_decimal
from ..services.status_updates import recompute_financials
from ..auth.deps import require_roles
from ..utils.audit import log_action
from ..services.documents import receipt_pdf
from fastapi import Response

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)

class PaymentIn(BaseModel):
    order_id: int
    amount: Decimal
    date: str | None = None
    method: str | None = None
    reference: str | None = None
    category: str | None = "ORDER"

@router.post("", response_model=dict, status_code=201)
def add_payment(
    body: PaymentIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if idempotency_key:
        existing = db.query(Payment).filter_by(idempotency_key=idempotency_key).one_or_none()
        if existing:
            return {"payment_id": existing.id, "order_balance": float(order.balance)}
    pdate = date.fromisoformat(body.date) if body.date else date.today()
    amount = to_decimal(body.amount)
    p = Payment(
        order_id=order.id,
        amount=amount,
        date=pdate,
        method=body.method,
        reference=body.reference,
        category=body.category or "ORDER",
        idempotency_key=idempotency_key,
    )
    db.add(p)
    order.paid_amount = to_decimal(order.paid_amount) + amount
    recompute_financials(order)
    db.commit()
    db.refresh(order)
    log_action(db, current_user, "payment.add", f"payment_id={p.id}")
    return {"payment_id": p.id, "order_balance": float(order.balance)}

class VoidIn(BaseModel):
    reason: str | None = None

@router.post("/{payment_id}/void", response_model=dict)
def void_payment(payment_id: int, body: VoidIn, db: Session = Depends(get_session)):
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(404, "Payment not found")
    if p.status == "VOIDED":
        return {"ok": True, "status": "VOIDED"}
    p.status = "VOIDED"
    p.void_reason = body.reason or ""
    order = db.get(Order, p.order_id)
    order.paid_amount = to_decimal(order.paid_amount) - to_decimal(p.amount)
    recompute_financials(order)
    db.commit()
    db.refresh(order)
    return {"ok": True, "status": "VOIDED", "order_balance": float(order.balance)}

@router.get("/{payment_id}/receipt.pdf")
def get_payment_receipt_pdf(payment_id: int, db: Session = Depends(get_session)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    
    order = db.get(Order, payment.order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    
    pdf = receipt_pdf(order, payment)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="receipt_{payment.id}.pdf"'},
    )
