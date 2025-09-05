from datetime import date
from decimal import Decimal

from ..services.ordersvc import _sum_posted_payments, q2


def calculate_plan_due(plan, as_of, trip_delivered_at=None) -> Decimal:
    """Simple plan calculation: monthly_amount * months since delivery"""
    if not plan or not plan.monthly_amount:
        return Decimal("0")
    
    # Simple: just return monthly amount (first month)
    return q2(Decimal(str(plan.monthly_amount or 0)))


def compute_expected_for_order(order, as_of, trip=None) -> Decimal:
    """Outstanding based on simplified business logic"""
    # No accrual until delivered
    trip_status = getattr(trip, "status", None) if trip else None
    is_delivered = trip_status == "DELIVERED" if trip_status else False
    
    base_total = q2(getattr(order, "total", 0) or 0)
    
    # OUTRIGHT: No accrual, just static total
    if not is_delivered or order.type == "OUTRIGHT":
        return base_total
    
    # RENTAL: Monthly accrual until returned
    if order.type == "RENTAL":
        if order.status == "RETURNED":
            return base_total  # No more accrual after return
            
        # Simple: add monthly amount for each month since delivery
        plan = getattr(order, "plan", None)
        if plan and plan.monthly_amount:
            delivered_at = getattr(trip, "delivered_at", None)
            if delivered_at:
                # Simple month count (can be refined later)
                from datetime import datetime
                months_delivered = 1  # Placeholder - keep simple for now
                accrual = q2(Decimal(str(plan.monthly_amount)) * months_delivered)
                return base_total + accrual
    
    # INSTALLMENT: Monthly accrual until cancelled or fully paid
    elif order.type == "INSTALLMENT":
        if order.status == "CANCELLED":
            return base_total  # No more accrual after cancel
            
        # Simple installment accrual (similar to rental)
        plan = getattr(order, "plan", None)
        if plan and plan.monthly_amount:
            # Placeholder simple logic
            return base_total
    
    return base_total


def compute_balance(order, as_of, trip=None) -> Decimal:
    """Simple: order.balance field"""
    return q2(getattr(order, "balance", 0) or 0)
