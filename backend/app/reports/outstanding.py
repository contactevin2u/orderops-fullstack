from datetime import date
from decimal import Decimal

from ..services.ordersvc import _sum_posted_payments, q2


def months_elapsed(start_date, as_of, cutoff=None) -> int:
    if not start_date:
        return 0
    if as_of < start_date:
        return 0
    months = (as_of.year - start_date.year) * 12 + (as_of.month - start_date.month)
    if as_of.day >= start_date.day:
        months += 1
    if cutoff and as_of > cutoff:
        return months_elapsed(start_date, cutoff)
    return months


def calculate_plan_due(plan, as_of) -> Decimal:
    if not plan:
        return Decimal("0")
    order_obj = getattr(plan, "order", None)
    # Use trip delivery date instead of order delivery date
    trip_delivered_at = getattr(order_obj.trip, "delivered_at", None) if order_obj and hasattr(order_obj, "trip") else None
    start = plan.start_date or (trip_delivered_at.date() if trip_delivered_at else None)
    cutoff = getattr(order_obj, "returned_at", None) if order_obj else None
    months = min(
        months_elapsed(start, as_of, cutoff=cutoff),
        getattr(plan, "months", None) or 10 ** 6,
    )
    return q2(Decimal(plan.monthly_amount) * months)


def compute_expected_for_order(order, as_of) -> Decimal:
    # Check if order has been delivered via trip status
    trip = getattr(order, "trip", None)
    is_delivered = trip and getattr(trip, "status", None) == "DELIVERED"
    
    if order.status in {"CANCELLED", "RETURNED"}:
        child_total = sum((Decimal(ch.total or 0) for ch in getattr(order, "adjustments", []) or []), Decimal("0"))
        return q2(child_total)
    
    # Calculate upfront collection amount (always available for driver)
    one_time_net = q2((order.subtotal or 0) - (order.discount or 0))
    plan = getattr(order, "plan", None)
    upfront_billed = q2(getattr(plan, "upfront_billed_amount", 0) or 0)
    
    # Delivery-based charges (fees and ongoing plan accrual)
    delivery_based_amount = Decimal("0")
    if is_delivered:
        # Add fees only after delivery
        fees = q2((order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0))
        delivery_based_amount += fees
        
        # Add plan accrual only after delivery (subtract upfront already billed)
        plan_accrued = calculate_plan_due(plan, as_of)
        ongoing_plan_due = max(plan_accrued - upfront_billed, Decimal("0"))
        delivery_based_amount += ongoing_plan_due
    
    return q2(one_time_net + delivery_based_amount)


def compute_balance(order, as_of) -> Decimal:
    expected = compute_expected_for_order(order, as_of)
    paid = _sum_posted_payments(order) + sum(
        (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []), Decimal("0")
    )
    return q2(expected - paid)
