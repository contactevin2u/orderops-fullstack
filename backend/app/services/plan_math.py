from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from ..models import Plan


def months_elapsed(
    start: datetime | None, end: datetime | None = None, cutoff: datetime | None = None
) -> int:
    """Return whole months elapsed between ``start`` and ``end``.

    A month counts as elapsed if the ``end`` day-of-month is greater than or
    equal to the ``start`` day.  ``cutoff`` can be supplied to cap ``end`` at a
    specific datetime (e.g. order.returned_at).
    """
    if not isinstance(start, datetime):
        return 0
    end = end or datetime.utcnow()
    if cutoff and end > cutoff:
        end = cutoff
    y = end.year - start.year
    m = end.month - start.month
    d = end.day - start.day
    return max(y * 12 + m + (1 if d >= 0 else 0), 0)


def calculate_plan_due(plan: Plan | None, as_of: date) -> Decimal:
    """Return amount expected to be paid for ``plan`` as of ``as_of`` date."""
    if not plan or not getattr(plan, "order", None):
        return Decimal("0.00")

    start = getattr(plan, "start_date", None) or getattr(plan.order, "delivery_date", None)
    if not start:
        return Decimal("0.00")

    start_dt = (
        datetime.combine(start, datetime.min.time())
        if isinstance(start, date)
        else start
    )
    end_dt = (
        datetime.combine(as_of, datetime.min.time())
        if isinstance(as_of, date)
        else as_of
    )
    cutoff = getattr(plan.order, "returned_at", None)
    months = months_elapsed(start_dt, end_dt, cutoff=cutoff)

    pmonths = getattr(plan, "months", None)
    if pmonths is not None:
        try:
            max_months = int(pmonths)
            months = min(months, max_months)
        except Exception:
            pass

    amount = Decimal(str(plan.monthly_amount)) * Decimal(months)
    return amount.quantize(Decimal("0.01"))
