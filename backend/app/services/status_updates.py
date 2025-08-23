from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import Order
from .ordersvc import create_adjustment_order


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
    """Mark an order as cancelled and create an adjustment invoice."""
    order.status = "CANCELLED"
    if getattr(order, "plan", None):
        order.plan.status = "CANCELLED"
    if reason:
        order.notes = (order.notes or "") + f"\n[VOID] {reason}"
    charges = {
        k: getattr(order, k)
        for k in ["penalty_fee", "delivery_fee", "return_delivery_fee"]
        if getattr(order, k)
    }
    create_adjustment_order(db, order, "-I", [], charges)
    return order


def mark_returned(db: Session, order: Order, return_date: datetime | None = None) -> Order:
    """Mark an order as returned and create a return adjustment."""
    order.returned_at = return_date or datetime.utcnow()
    order.status = "RETURNED"
    if getattr(order, "plan", None):
        order.plan.status = "CANCELLED"
    charges = {
        k: getattr(order, k)
        for k in ["return_delivery_fee", "penalty_fee"]
        if getattr(order, k)
    }
    create_adjustment_order(db, order, "-R", [], charges)
    return order


def apply_buyback(
    db: Session, order: Order, amount: Decimal, discount: dict | None = None
) -> Order:
    """Apply a buyback amount to an order and generate an adjustment."""
    if order.type != "OUTRIGHT":
        raise ValueError("Buyback only allowed for OUTRIGHT orders")
    amt = Decimal(str(amount))
    if amt <= 0:
        raise ValueError("Invalid buyback amount")

    disc_amt = Decimal("0")
    if discount:
        dtype = discount.get("type")
        dval = Decimal(str(discount.get("value", 0)))
        if dtype == "percent":
            disc_amt = (amt * dval / Decimal("100")).quantize(Decimal("0.01"))
        elif dtype == "fixed":
            disc_amt = dval

    line_amt = amt - disc_amt
    lines = [
        {
            "name": "BUYBACK",
            "item_type": "OUTRIGHT",
            "qty": 1,
            "unit_price": -line_amt,
            "line_total": -line_amt,
        }
    ]
    create_adjustment_order(db, order, "-I", lines, {})
    order.status = "CANCELLED"
    if getattr(order, "plan", None):
        order.plan.status = "CANCELLED"
    return order
