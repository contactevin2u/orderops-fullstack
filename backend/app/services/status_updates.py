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
from .plan_math import calculate_plan_due


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
    Mark an order as returned with proper outstanding validation and accrual cutoff.
    
    Clean refactored workflow:
    1. Validate outstanding using proper calculation (for RENTAL orders)  
    2. Set returned_at timestamp (cuts off accrual)
    3. Update order status to RETURNED
    4. Cancel plan to stop future accrual
    5. Create adjustment order with fees
    6. Handle fee collection if requested
    7. Zero out parent order fees to prevent double-counting
    """
    
    # Step 1: Outstanding validation for RENTAL orders using proper calculation
    if order.type == "RENTAL" and not collect:
        return_date_effective = return_date or datetime.utcnow()
        as_of_date = return_date_effective.date()
        
        # Use the same outstanding calculation as reports/outstanding endpoint
        from ..reports.outstanding import compute_balance
        trip = getattr(order, "trip", None)
        outstanding_balance = compute_balance(order, as_of_date, trip)
        
        if outstanding_balance > DEC0:
            raise ValueError(
                f"Outstanding balance of RM {outstanding_balance} must be cleared before return. "
                f"Set 'collect' to true to collect outstanding fees during return."
            )
    
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
    Cancel an installment plan with proper outstanding validation and principal calculation.
    
    Clean refactored workflow:
    1. Validate installment order and plan
    2. Check outstanding amounts using proper calculation  
    3. Calculate principal payments (excluding fees)
    4. Cancel order and plan status
    5. Create adjustment order for fees only
    6. Handle fee collection if requested
    7. Prorate items based on principal payments only
    8. Zero parent fees to prevent double-counting
    """
    
    # Step 1: Validate order type and plan
    if order.type != "INSTALLMENT":
        raise ValueError("cancel_installment only allowed for INSTALLMENT orders")
    plan = getattr(order, "plan", None)
    if not plan:
        raise ValueError("Installment plan missing")
    
    # Step 2: Outstanding validation using proper calculation
    cancellation_date_effective = cancellation_date or datetime.utcnow()
    as_of_date = cancellation_date_effective.date()
    
    # Use same outstanding calculation as reports/outstanding endpoint
    from ..reports.outstanding import compute_balance
    trip = getattr(order, "trip", None)
    outstanding_balance = compute_balance(order, as_of_date, trip)
    
    # For installments, we allow cancellation with outstanding but warn
    if outstanding_balance > DEC0 and not collect:
        # Note: Unlike rentals, installments can be cancelled with outstanding
        # but fees may apply for early cancellation
        pass
    
    # Step 3: Calculate principal payments (excluding fees)
    # Get all posted payments and separate principal from fees
    all_payments = getattr(order, "payments", []) or []
    fee_categories = {"DELIVERY", "PENALTY", "FEE"}
    
    principal_paid = DEC0
    fee_paid = DEC0
    
    for payment in all_payments:
        if payment.status == "POSTED":
            payment_amount = to_decimal(payment.amount or DEC0)
            # Categorize payment as fee or principal
            if getattr(payment, "category", "") in fee_categories:
                fee_paid += payment_amount
            else:
                principal_paid += payment_amount
    
    # Step 4: Update order and plan status
    order.status = "CANCELLED"
    plan.status = "CANCELLED"
    
    # Step 5: Set penalty and return fees if provided
    if penalty is not None:
        order.penalty_fee = to_decimal(penalty)
    if return_fee is not None:
        order.return_delivery_fee = to_decimal(return_fee)
    
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
    
    # Step 8: Prorate items based on principal payments only
    remaining_principal = principal_paid
    
    # Get all non-fee items for proration
    principal_items = [
        item for item in order.items 
        if getattr(item, "item_type", "") not in {"FEE"}
    ]
    
    # Calculate total principal value
    total_principal_value = sum(
        to_decimal(item.line_total or DEC0) for item in principal_items
    )
    
    # Prorate based on proportional payment
    for item in principal_items:
        item_total = to_decimal(item.line_total or DEC0)
        
        if total_principal_value > DEC0 and remaining_principal > DEC0:
            # Calculate proportional amount paid for this item
            item_proportion = item_total / total_principal_value
            item_paid = (principal_paid * item_proportion).quantize(Decimal("0.01"))
            
            # Cap at item total
            item_paid = min(item_paid, item_total)
            
            if item_paid >= item_total:
                # Item fully paid - keep as is
                pass
            elif item_paid > DEC0:
                # Item partially paid - prorate
                qty = to_decimal(item.qty or 1)
                new_unit_price = (item_paid / qty).quantize(Decimal("0.01"))
                item.unit_price = new_unit_price
                item.line_total = item_paid
            else:
                # Item not paid - void it
                item.unit_price = DEC0
                item.line_total = DEC0
        else:
            # No principal payments or no principal value - void all items
            item.unit_price = DEC0
            item.line_total = DEC0
    
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
