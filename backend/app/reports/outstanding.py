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
    start = plan.start_date or (order_obj.delivery_date if order_obj else None)
    cutoff = getattr(order_obj, "returned_at", None) if order_obj else None
    months = min(
        months_elapsed(start, as_of, cutoff=cutoff),
        getattr(plan, "months", None) or 10 ** 6,
    )
    return q2(Decimal(plan.monthly_amount) * months)


def compute_expected_for_order(order, as_of) -> Decimal:
    fees = q2((order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0))
    if order.status in {"CANCELLED", "RETURNED"}:
        child_total = sum((Decimal(ch.total or 0) for ch in getattr(order, "adjustments", []) or []), Decimal("0"))
        return q2(child_total)
    plan_due = calculate_plan_due(getattr(order, "plan", None), as_of)
    if plan_due > 0:
        return q2(plan_due + fees)
    return q2(order.total or 0)


def compute_balance(order, as_of) -> Decimal:
    expected = compute_expected_for_order(order, as_of)
    paid = _sum_posted_payments(order) + sum(
        (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []), Decimal("0")
    )
    return q2(expected - paid)
