from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from datetime import date

from ..models import Order, Payment
from ..utils.normalize import to_decimal
from .ordersvc import (
    create_adjustment_order,
    recompute_financials,
    CONST_CANCEL_SUFFIX,
    CONST_RETURN_SUFFIX,
    CONST_BUYBACK_SUFFIX,
)
# Removed plan_math import


DEC0 = Decimal("0.00")


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
    create_adjustment_order(db, order, CONST_CANCEL_SUFFIX, [], charges)
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
    """
    SIMPLIFIED rental return:
    1. Set returned_at (stops accrual)
    2. Update status to RETURNED  
    3. Apply return delivery fee (user entered)
    4. Create adjustment for fees
    """
    
    # Skip complex validation
    
    # Step 2: Set returned_at timestamp - this cuts off all future accrual
    order.returned_at = return_date or datetime.utcnow()
    
    # Step 3: Update order status  
    order.status = "RETURNED"
    
    # Step 4: Cancel plan to stop future accrual
    plan = getattr(order, "plan", None)
    if plan:
        plan.status = "CANCELLED"
    
    # Step 5: Update return delivery fee if provided
    if return_delivery_fee is not None:
        order.return_delivery_fee = to_decimal(return_delivery_fee)
    
    # Step 6: Create adjustment order with fees (before zeroing parent)
    # Include both return_delivery_fee and penalty_fee in adjustment
    charges = {}
    if order.return_delivery_fee and order.return_delivery_fee > DEC0:
        charges["return_delivery_fee"] = order.return_delivery_fee
    if order.penalty_fee and order.penalty_fee > DEC0:
        charges["penalty_fee"] = order.penalty_fee
        
    adj_order = None
    if charges:
        adj_order = create_adjustment_order(db, order, CONST_RETURN_SUFFIX, [], charges)
    
    # Step 7: Handle fee collection if requested
    if collect and adj_order and adj_order.total > DEC0:
        payment = Payment(
            order_id=adj_order.id,
            amount=adj_order.total,
            date=payment_date or date.today(),
            category="RETURN_FEES",
            method=method or "CASH",
            reference=reference,
            status="POSTED",
        )
        db.add(payment)
        
        # Update adjustment order balances
        adj_order.paid_amount = adj_order.total
        adj_order.balance = DEC0
    
    # Step 8: Zero out parent order fees to prevent double-counting
    # This must happen AFTER adjustment order creation
    order.return_delivery_fee = DEC0
    order.penalty_fee = DEC0
    
    # Step 9: Recompute parent order financials
    recompute_financials(order)
    
    db.flush()  # Ensure all changes are persisted
    
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
    cancellation_date: datetime | None = None,
) -> Order:
    """
    SIMPLIFIED installment cancellation:
    1. Apply penalty fee (user entered)
    2. Apply return delivery fee (user entered)  
    3. Cancel installment plan (stops accrual)
    4. Create adjustment for fees only
    """
    
    # Step 1: Validate order type and plan
    if order.type != "INSTALLMENT":
        raise ValueError("cancel_installment only allowed for INSTALLMENT orders")
    plan = getattr(order, "plan", None)
    if not plan:
        raise ValueError("Installment plan missing")
    
    # Simple: Set penalty and return fees (user entered amounts)
    if penalty is not None:
        order.penalty_fee = to_decimal(penalty)
    if return_fee is not None:
        order.return_delivery_fee = to_decimal(return_fee)
    
    # Cancel order and plan (stops accrual)
    order.status = "CANCELLED"
    plan.status = "CANCELLED"
    
    # Step 6: Create adjustment order for fees (before zeroing parent)
    charges = {}
    if order.penalty_fee and order.penalty_fee > DEC0:
        charges["penalty_fee"] = order.penalty_fee
    if order.return_delivery_fee and order.return_delivery_fee > DEC0:
        charges["return_delivery_fee"] = order.return_delivery_fee
    
    adj_order = None
    if charges:
        adj_order = create_adjustment_order(db, order, CONST_CANCEL_SUFFIX, [], charges)
    
    # Step 7: Handle fee collection if requested (on adjustment order only)
    if collect and adj_order and adj_order.total > DEC0:
        payment = Payment(
            order_id=adj_order.id,  # Payment goes to adjustment order, NOT parent
            amount=adj_order.total,
            date=payment_date or date.today(),
            category="CANCELLATION_FEES",
            method=method or "CASH",
            reference=reference,
            status="POSTED",
        )
        db.add(payment)
        
        # Update adjustment order balances only
        adj_order.paid_amount = adj_order.total
        adj_order.balance = DEC0
    
    # Step 8: Keep original order items unchanged (simplified business logic)
    # User-entered penalty and return delivery fees are handled via adjustment orders only
    
    # Step 9: Zero out parent order fees to prevent double-counting  
    # This must happen AFTER adjustment order creation
    order.penalty_fee = DEC0
    order.return_delivery_fee = DEC0
    
    # Step 10: Recompute parent order financials
    recompute_financials(order)
    
    db.flush()  # Ensure all changes are persisted
    
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
    create_adjustment_order(db, order, CONST_BUYBACK_SUFFIX, lines, {})

    # Record refund as negative payment
    p = Payment(
        order_id=order.id,
        amount=-line_amt,
        date=payment_date or date.today(),
        category="BUYBACK",
        method=method,
        reference=reference,
        status="POSTED",
    )
    db.add(p)
    order.paid_amount = to_decimal(order.paid_amount) - line_amt
    recompute_financials(order)
    return order
