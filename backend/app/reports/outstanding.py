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
    """Simple: just return order.total"""
    return q2(getattr(order, "total", 0) or 0)


def compute_balance(order, as_of, trip=None) -> Decimal:
    """Simple: order.balance field"""
    return q2(getattr(order, "balance", 0) or 0)
