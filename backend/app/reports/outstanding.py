from datetime import date
from decimal import Decimal

from ..services.ordersvc import _sum_posted_payments, q2


def months_elapsed(start_date, as_of, cutoff=None) -> int:
    """Calculate months elapsed from start_date to as_of, with proper cutoff handling"""
    if not start_date:
        return 0
    if as_of < start_date:
        return 0
        
    # Apply cutoff first if it exists and is before as_of
    end_date = as_of
    if cutoff and cutoff < as_of:
        end_date = cutoff
    
    # Calculate full months elapsed
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    
    # Add 1 if we've passed the start day in the current month
    if end_date.day >= start_date.day:
        months += 1
        
    return max(0, months)


def calculate_plan_due(plan, as_of, trip_delivered_at=None) -> Decimal:
    """Calculate plan due amount with explicit trip delivery date."""
    if not plan:
        return Decimal("0")
    
    order_obj = getattr(plan, "order", None)
    
    # Start date priority: plan.start_date > trip_delivered_at > order.delivery_date
    start = plan.start_date
    if not start and trip_delivered_at:
        start = trip_delivered_at.date() if hasattr(trip_delivered_at, 'date') else trip_delivered_at
    if not start and order_obj and order_obj.delivery_date:
        start = order_obj.delivery_date.date() if hasattr(order_obj.delivery_date, 'date') else order_obj.delivery_date
    
    if not start:
        return Decimal("0")
    
    cutoff = getattr(order_obj, "returned_at", None) if order_obj else None
    if cutoff and hasattr(cutoff, 'date'):
        cutoff = cutoff.date()
    
    months = min(
        months_elapsed(start, as_of, cutoff=cutoff),
        getattr(plan, "months", None) or 10 ** 6,
    )
    return q2(Decimal(str(plan.monthly_amount or 0)) * months)


def compute_expected_for_order(order, as_of, trip=None) -> Decimal:
    """Calculate expected amount for order with explicit trip data."""
    # Use passed trip or get from order relationship
    if trip is None:
        trip = getattr(order, "trip", None)
    
    # Check for delivered status - could be DELIVERED, SUCCESS, or COMPLETED
    trip_status = getattr(trip, "status", None) if trip else None
    is_delivered = trip_status in {"DELIVERED", "SUCCESS", "COMPLETED"} if trip_status else False
    trip_delivered_at = getattr(trip, "delivered_at", None) if trip else None
    
    if order.status in {"CANCELLED", "RETURNED"}:
        # For cancelled/returned orders, only count adjustment totals (fees, penalties, etc.)
        child_total = sum((Decimal(ch.total or 0) for ch in getattr(order, "adjustments", []) or []), Decimal("0"))
        return q2(child_total)
    
    plan = getattr(order, "plan", None)
    order_type = (getattr(order, "type", "") or "").upper()
    
    # Base calculation components
    subtotal = q2(getattr(order, "subtotal", 0) or 0)
    discount = q2(getattr(order, "discount", 0) or 0)
    delivery_fee = q2(getattr(order, "delivery_fee", 0) or 0)
    return_delivery_fee = q2(getattr(order, "return_delivery_fee", 0) or 0)
    penalty_fee = q2(getattr(order, "penalty_fee", 0) or 0)
    
    # For OUTRIGHT orders: always include full amount regardless of delivery
    if order_type == "OUTRIGHT":
        return q2(subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee)
    
    # For RENTAL/INSTALLMENT orders: more complex logic
    upfront_billed = q2(Decimal(str(getattr(plan, "upfront_billed_amount", 0) or 0))) if plan else Decimal("0")
    
    # Always include upfront amount and fees
    base_amount = q2(subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee)
    
    # Add ongoing plan accrual only if delivered
    plan_accrual = Decimal("0")
    if is_delivered and plan and plan.monthly_amount:
        total_plan_due = calculate_plan_due(plan, as_of, trip_delivered_at)
        
        # By convention, first month is always included in order items/subtotal
        # Only accrue additional months beyond the first
        start = plan.start_date
        if not start and trip_delivered_at:
            start = trip_delivered_at.date() if hasattr(trip_delivered_at, 'date') else trip_delivered_at
        if not start and order and getattr(order, 'delivery_date', None):
            start = order.delivery_date.date() if hasattr(order.delivery_date, 'date') else order.delivery_date
            
        cutoff = getattr(order, "returned_at", None) if order else None
        if cutoff and hasattr(cutoff, 'date'):
            cutoff = cutoff.date()
            
        if start:
            months = min(
                months_elapsed(start, as_of, cutoff=cutoff),
                getattr(plan, "months", None) or 10 ** 6,
            )
            additional_months = max(months - 1, 0)  # Exclude first month (always in subtotal)
            plan_accrual = q2(Decimal(str(plan.monthly_amount or 0)) * additional_months)
        
    return q2(base_amount + plan_accrual)


def compute_balance(order, as_of, trip=None) -> Decimal:
    """Calculate balance with explicit trip data."""
    expected = compute_expected_for_order(order, as_of, trip)
    paid = _sum_posted_payments(order) + sum(
        (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []), Decimal("0")
    )
    return q2(expected - paid)
