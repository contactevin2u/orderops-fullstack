from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from datetime import date

from ..models import Order, Payment
from ..utils.normalize import to_decimal
from .ordersvc import create_adjustment_order
from .plan_math import calculate_plan_due


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
    order.balance = (order.total - (order.paid_amount or DEC0)).quantize(
        Decimal("0.01")
    )


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


def mark_returned(
    db: Session,
    order: Order,
    return_date: datetime | None = None,
    return_delivery_fee: Decimal | None = None,
    collect: bool = False,
    method: str | None = None,
    reference: str | None = None,
    payment_date: date | None = None,
) -> Order:
    """Mark an order as returned and handle optional return delivery fee."""
    if order.type == "RENTAL":
        as_of = (return_date.date() if return_date else date.today())
        paid = sum(
            (
                p.amount
                for p in getattr(order, "payments", [])
                if p.status == "POSTED" and p.date <= as_of
            ),
            DEC0,
        )
        fees = (
            (order.delivery_fee or DEC0)
            + (order.return_delivery_fee or DEC0)
            + (order.penalty_fee or DEC0)
        )
        expected = calculate_plan_due(getattr(order, "plan", None), as_of) + fees
        balance = (expected - paid).quantize(Decimal("0.01"))
        if balance > DEC0:
            raise ValueError("Outstanding must be cleared before return")
    order.returned_at = return_date or datetime.utcnow()
    order.status = "RETURNED"
    if return_delivery_fee is not None:
        order.return_delivery_fee = to_decimal(return_delivery_fee)
    if getattr(order, "plan", None):
        order.plan.status = "CANCELLED"
    charges = {
        k: getattr(order, k)
        for k in ["return_delivery_fee", "penalty_fee"]
        if getattr(order, k)
    }
    adj = create_adjustment_order(db, order, "-R", [], charges)
    rdf = to_decimal(order.return_delivery_fee or DEC0)
    if collect and rdf > DEC0:
        p = Payment(
            order_id=adj.id,
            amount=rdf,
            date=payment_date or date.today(),
            category="DELIVERY",
            method=method,
            reference=reference,
        )
        db.add(p)
        adj.paid_amount = to_decimal(adj.paid_amount) + rdf
        adj.balance = (adj.total - adj.paid_amount).quantize(Decimal("0.01"))
    order.return_delivery_fee = DEC0
    order.penalty_fee = DEC0
    recompute_financials(order)
    return order


def cancel_installment(
    db: Session,
    order: Order,
    penalty: Decimal | None = None,
    return_fee: Decimal | None = None,
    collect: bool = False,
    method: str | None = None,
    reference: str | None = None,
    payment_date: date | None = None,
) -> Order:
    """Cancel an installment plan voiding unpaid principal.

    Only penalty and return delivery charges remain payable after
    cancellation. When ``collect`` is true these fees are immediately
    collected and the order balance becomes zero.
    """
    if order.type != "INSTALLMENT":
        raise ValueError("cancel_installment only allowed for INSTALLMENT orders")
    if not getattr(order, "plan", None):
        raise ValueError("Installment plan missing")

    order.status = "CANCELLED"
    order.plan.status = "CANCELLED"
    if penalty is not None:
        order.penalty_fee = to_decimal(penalty)
    if return_fee is not None:
        order.return_delivery_fee = to_decimal(return_fee)

    charges_total = (order.penalty_fee or DEC0) + (order.return_delivery_fee or DEC0)
    charges = {
        k: getattr(order, k)
        for k in ["return_delivery_fee", "penalty_fee"]
        if getattr(order, k)
    }
    create_adjustment_order(db, order, "-I", [], charges)

    original_paid = to_decimal(order.paid_amount or DEC0)
    payments: list[Payment] = []
    if collect:
        if order.penalty_fee and order.penalty_fee > DEC0:
            payments.append(
                Payment(
                    order_id=order.id,
                    amount=to_decimal(order.penalty_fee),
                    date=payment_date or date.today(),
                    category="PENALTY",
                    method=method,
                    reference=reference,
                )
            )
        if order.return_delivery_fee and order.return_delivery_fee > DEC0:
            payments.append(
                Payment(
                    order_id=order.id,
                    amount=to_decimal(order.return_delivery_fee),
                    date=payment_date or date.today(),
                    category="DELIVERY",
                    method=method,
                    reference=reference,
                )
            )
    for p in payments:
        db.add(p)
        order.paid_amount = to_decimal(order.paid_amount) + to_decimal(p.amount)

    principal_paid = original_paid
    remaining = principal_paid
    for it in order.items:
        if getattr(it, "item_type", "") == "FEE":
            continue
        lt = to_decimal(it.line_total or DEC0)
        if remaining <= DEC0:
            it.unit_price = DEC0
            it.line_total = DEC0
        elif remaining >= lt:
            remaining -= lt
        else:
            qty = to_decimal(it.qty or 1)
            unit_price = (remaining / qty).quantize(Decimal("0.01"))
            it.unit_price = unit_price
            it.line_total = remaining
            remaining = DEC0

    recompute_financials(order)
    return order


def apply_buyback(
    db: Session,
    order: Order,
    amount: Decimal,
    discount: dict | None = None,
    method: str | None = None,
    reference: str | None = None,
    payment_date: date | None = None,
    return_date: datetime | None = None,
) -> Order:
    """Apply a buyback amount to an order and generate an adjustment.

    Creates a negative payment entry representing the refund and adjusts
    order financials accordingly.
    """
    if order.type != "OUTRIGHT":
        raise ValueError("Buyback only allowed for OUTRIGHT orders")
    amt = Decimal(str(amount))
    if amt <= 0:
        raise ValueError("Invalid buyback amount")

    disc_amt = Decimal("0")
    if discount:
        dtype = discount.get("type")
        dval = Decimal(str(discount.get("value", 0)))
        if dval < 0:
            raise ValueError("Invalid discount value")
        if dtype == "percent":
            dval = min(max(dval, Decimal("0")), Decimal("100"))
            disc_amt = (amt * dval / Decimal("100")).quantize(Decimal("0.01"))
        elif dtype == "fixed":
            if dval > amt:
                raise ValueError("Discount exceeds buyback amount")
            disc_amt = dval
        else:
            raise ValueError("Invalid discount type")

    line_amt = amt - disc_amt
    order.status = "RETURNED"
    # timestamp the buyback event
    order.returned_at = return_date or datetime.utcnow()
    if getattr(order, "plan", None):
        order.plan.status = "CANCELLED"
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

    # Record refund as negative payment
    p = Payment(
        order_id=order.id,
        amount=-line_amt,
        date=payment_date or date.today(),
        category="BUYBACK",
        method=method,
        reference=reference,
    )
    db.add(p)
    order.paid_amount = to_decimal(order.paid_amount) - line_amt
    recompute_financials(order)
    return order
