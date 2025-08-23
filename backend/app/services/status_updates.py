from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import Order


DEC0 = Decimal("0.00")


def recompute_financials(order: Order) -> None:
    """Recalculate subtotal, total and balance for ``order`` based on items and charges."""
    subtotal = sum(
        (
            it.line_total if it.line_total is not None else (it.unit_price * it.qty)
            for it in order.items
        ),
        DEC0,
    ).quantize(Decimal("0.01"))
    order.subtotal = subtotal
    order.total = (
        subtotal
        - (order.discount or DEC0)
        + (order.delivery_fee or DEC0)
        + (order.return_delivery_fee or DEC0)
        + (order.penalty_fee or DEC0)
    ).quantize(Decimal("0.01"))
    order.balance = (order.total - (order.paid_amount or DEC0)).quantize(Decimal("0.01"))


def mark_cancelled(db: Session, order: Order, reason: str | None = None) -> Order:
    """Mark an order as cancelled and recompute monetary fields."""
    order.status = "CANCELLED"
    if reason:
        order.notes = (order.notes or "") + f"\n[VOID] {reason}"
    paid_total = sum(
        (p.amount for p in getattr(order, "payments", []) if getattr(p, "status", "POSTED") == "POSTED"),
        Decimal("0"),
    )
    if paid_total == Decimal("0"):
        order.total = Decimal("0")
        order.balance = Decimal("0")
    else:
        recompute_financials(order)
    db.commit()
    db.refresh(order)
    return order


def mark_returned(db: Session, order: Order, return_date: datetime | None = None) -> Order:
    """Mark an order as returned, optionally recording a return date."""
    order.returned_at = return_date or datetime.utcnow()
    order.status = "RETURNED"
    recompute_financials(order)
    db.commit()
    db.refresh(order)
    return order


def apply_buyback(db: Session, order: Order, amount: Decimal) -> Order:
    """Apply a buyback amount to an order and mark it as returned."""
    if order.type != "OUTRIGHT":
        raise ValueError("Buyback only allowed for OUTRIGHT orders")
    amt = Decimal(str(amount))
    if amt <= 0:
        raise ValueError("Invalid buyback amount")
    order.discount = (order.discount or Decimal("0")) + amt
    order.status = "RETURNED"
    recompute_financials(order)
    db.commit()
    db.refresh(order)
    return order
