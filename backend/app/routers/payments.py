from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, condecimal
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from ..db import get_session
from ..models import Payment, Order

router = APIRouter(prefix="/payments", tags=["payments"])


# ---- Pydantic request bodies -------------------------------------------------

class PaymentIn(BaseModel):
    order_id: int
    # Use Decimal with 2dp for currency; Pydantic will coerce from "250.00" or 250
    amount: condecimal(max_digits=12, decimal_places=2)
    date: str | None = None           # ISO date: "YYYY-MM-DD"
    method: str | None = None         # e.g., "cash", "bank", "tng"
    reference: str | None = None      # e.g., cheque no / txn id
    category: str | None = "ORDER"    # one of: ORDER / PENALTY / RETURN_FEE etc.


class VoidIn(BaseModel):
    reason: str | None = None


# ---- Helpers -----------------------------------------------------------------

TWO_DP = Decimal("0.01")

def to_decimal(x) -> Decimal:
    """Convert None/float/str/Decimal to Decimal safely."""
    if isinstance(x, Decimal):
        return x
    if x is None:
        return Decimal("0")
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        # Fallback to 0 if something odd arrives
        return Decimal("0")

def q2(x: Decimal) -> Decimal:
    """Quantize to 2 decimal places."""
    return to_decimal(x).quantize(TWO_DP, rounding=ROUND_HALF_UP)


# ---- Routes ------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201)
def add_payment(body: PaymentIn, db: Session = Depends(get_session)):
    # 1) Validate order
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2) Parse/validate date
    if body.date:
        try:
            pdate = date.fromisoformat(body.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD")
    else:
        pdate = date.today()

    # 3) Amount as Decimal (currency-safe)
    amt = q2(body.amount)
    if amt <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Amount must be > 0")

    # 4) Create the payment
    payment = Payment(
        order_id=order.id,
        amount=amt,
        date=pdate,
        method=body.method,
        reference=body.reference,
        category=body.category or "ORDER",
        # status defaults to POSTED in the model/migration
    )
    db.add(payment)
    db.flush()  # ensure payment.id is assigned

    # 5) Recalculate paid & balance (Decimal-only math)
    current_paid = to_decimal(getattr(order, "paid_amount", None))
    new_paid = q2(current_paid + amt)

    order_total = to_decimal(getattr(order, "total", None))
    new_balance = q2(order_total - new_paid)

    # Persist fields (these are Numeric/Decimal columns)
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
    # 1) Validate payment
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Already voided? idempotent response
    if getattr(payment, "status", "") == "VOIDED":
        order = db.get(Order, payment.order_id)
        return {
            "ok": True,
            "status": "VOIDED",
            "order_id": payment.order_id,
            "order_paid_amount": str(getattr(order, "paid_amount", Decimal("0.00")) if order else "0.00"),
            "order_balance": str(getattr(order, "balance", Decimal("0.00")) if order else "0.00"),
        }

    # 2) Mark void
    payment.status = "VOIDED"
    payment.void_reason = (body.reason or "").strip()

    # 3) Recalculate order paid/balance
    order = db.get(Order, payment.order_id)
    if not order:
        # Shouldn't happen, but guard anyway
        db.commit()
        return {"ok": True, "status": "VOIDED", "order_id": payment.order_id}

    current_paid = to_decimal(getattr(order, "paid_amount", None))
    amt = to_decimal(getattr(payment, "amount", None))

    new_paid = q2(current_paid - amt)
    if new_paid < Decimal("0"):
        new_paid = Decimal("0.00")

    order_total = to_decimal(getattr(order, "total", None))
    new_balance = q2(order_total - new_paid)

    order.paid_amount = new_paid
    order.balance = new_balance

    db.commit()
    db.refresh(order)

    return {
        "ok": True,
        "status": "VOIDED",
        "payment_id": payment.id,
        "order_id": order.id,
        "order_paid_amount": str(order.paid_amount),
        "order_balance": str(order.balance),
    }
