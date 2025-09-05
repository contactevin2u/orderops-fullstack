from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ..services.ordersvc import _sum_posted_payments, q2

DELIVERED_STATUSES = {"DELIVERED", "SUCCESS", "COMPLETED"}
DEC0 = Decimal("0")


def _as_date(d: Optional[datetime | date]) -> Optional[date]:
    """Convert datetime or date to date, or None"""
    if not d:
        return None
    return d.date() if isinstance(d, datetime) else d


def months_between(start: Optional[date], as_of: date, cutoff: Optional[date] = None) -> int:
    """
    Count billing months inclusive of the start month.
    Returns 0 if start is None or start > as_of.
    Applies cutoff if provided (e.g., returned_at/cancelled_at).
    """
    if not start or as_of < start:
        return 0
    end = as_of
    if cutoff and cutoff < end:
        end = cutoff
        if end < start:
            return 0
    # full months + include current month if day-of-month reached
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= start.day:
        months += 1
    return max(0, months)


def _resolve_start_and_cutoff(order, trip) -> tuple[Optional[date], Optional[date], bool]:
    """Resolve billing start date, cutoff date, and delivery status"""
    # delivery gating
    trip_status = getattr(trip, "status", None) if trip else None
    is_delivered = trip_status in DELIVERED_STATUSES if trip_status else False

    delivered_at = getattr(trip, "delivered_at", None) if trip else None
    delivery_date = getattr(order, "delivery_date", None)

    # start priority: plan.start_date > trip.delivered_at > order.delivery_date
    plan = getattr(order, "plan", None)
    start = getattr(plan, "start_date", None)
    start = _as_date(start) or _as_date(delivered_at) or _as_date(delivery_date)

    # cutoff: returned_at (rental) or cancelled_at (installment) if present
    cutoff = getattr(order, "returned_at", None) or getattr(order, "cancelled_at", None)
    cutoff = _as_date(cutoff)

    return start, cutoff, is_delivered


def calculate_plan_due(plan, as_of: date, trip_delivered_at: Optional[datetime] = None) -> Decimal:
    """
    Total plan due from start through as_of (includes the first month).
    For INSTALLMENT, cap by plan.months. For RENTAL, unlimited.
    """
    if not plan or not getattr(plan, "monthly_amount", None):
        return DEC0

    # Resolve start
    start = _as_date(getattr(plan, "start_date", None))
    if not start and trip_delivered_at:
        start = _as_date(trip_delivered_at)
    if not start:
        # If no start can be resolved, nothing accrues
        return DEC0

    months = months_between(start, as_of, cutoff=_as_date(getattr(getattr(plan, "order", None), "returned_at", None)))
    if months <= 0:
        return DEC0

    # Cap for INSTALLMENT
    plan_type = (getattr(plan, "plan_type", None) or getattr(getattr(plan, "order", None), "type", "") or "").upper()
    if plan_type == "INSTALLMENT":
        max_months = int(getattr(plan, "months", 0) or 0)
        if max_months > 0:
            months = min(months, max_months)

    return q2(Decimal(str(plan.monthly_amount)) * months)


def compute_expected_for_order(order, as_of: date, trip=None) -> Decimal:
    """
    Expected amount = base (which already contains first month in items/fees) + accrual for additional months.
    Base components: subtotal - discount + all fee fields on the order (delivery, return, penalty).
    Accrual applies only after delivery and stops at return/cancel.
    """
    order_type = (getattr(order, "type", "") or "").upper()
    subtotal = q2(getattr(order, "subtotal", 0) or 0)
    discount = q2(getattr(order, "discount", 0) or 0)
    delivery_fee = q2(getattr(order, "delivery_fee", 0) or 0)
    return_delivery_fee = q2(getattr(order, "return_delivery_fee", 0) or 0)
    penalty_fee = q2(getattr(order, "penalty_fee", 0) or 0)

    base = q2(subtotal - discount + delivery_fee + return_delivery_fee + penalty_fee)

    # OUTRIGHT: static
    if order_type == "OUTRIGHT":
        return base

    # Resolve delivery start/cutoff and gate accrual
    start, cutoff, is_delivered = _resolve_start_and_cutoff(order, trip)
    plan = getattr(order, "plan", None)
    monthly_amount = q2(getattr(plan, "monthly_amount", 0) or 0)

    # If not delivered or no plan/monthly, no accrual beyond base
    if not is_delivered or monthly_amount <= DEC0 or not start:
        return base

    # Months since start (inclusive); month 1 is already in base (first month included in items)
    months = months_between(start, as_of, cutoff=cutoff)
    additional_months = max(months - 1, 0)

    # Cap INSTALLMENT by plan.months (beyond the first month already in base)
    if order_type == "INSTALLMENT":
        total_months = int(getattr(plan, "months", 0) or 0)
        if total_months > 0:
            additional_months = min(additional_months, max(total_months - 1, 0))

    accrual = q2(monthly_amount * additional_months)
    return q2(base + accrual)


def compute_balance(order, as_of: date, trip=None) -> Decimal:
    """
    Balance = expected - all posted payments on order + adjustments (child orders).
    Includes posted payments on the order and its adjustments.
    """
    expected = compute_expected_for_order(order, as_of, trip)
    paid_parent = _sum_posted_payments(order)
    paid_adjustments = sum((_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []), DEC0)
    return q2(expected - q2(paid_parent + paid_adjustments))
