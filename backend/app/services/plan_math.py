from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from ..models import Plan


def months_elapsed(start: datetime | None, end: datetime | None = None) -> int:
    """Return whole months elapsed between ``start`` and ``end``.

    A month counts as elapsed if the ``end`` day-of-month is greater than or
    equal to the ``start`` day.  This mirrors billing cycles where payment is
    due on the same day each month.  Examples::

        start=15 Jan, end=14 Feb -> 1 month
        start=15 Jan, end=15 Feb -> 2 months

    ``start`` can be ``None``; in that case ``0`` is returned.
    """
    if not isinstance(start, datetime):
        return 0
    end = end or datetime.utcnow()
    y = end.year - start.year
    m = end.month - start.month
    d = end.day - start.day
    return max(y * 12 + m + (1 if d >= 0 else 0), 0)


def calculate_plan_due(plan: Plan | None, as_of: date) -> Decimal:
    """Return amount expected to be paid for ``plan`` as of ``as_of`` date."""
    if not plan or not getattr(plan, "order", None) or not plan.order.delivery_date:
        return Decimal("0.00")

    end_dt = datetime.combine(as_of, datetime.min.time()) if isinstance(as_of, date) else as_of
    months = months_elapsed(plan.order.delivery_date, end_dt)

    if plan.plan_type == "INSTALLMENT" and plan.months:
        try:
            max_months = int(plan.months)
            months = min(months, max_months)
        except Exception:
            pass

    amount = Decimal(str(plan.monthly_amount)) * Decimal(months)
    return amount.quantize(Decimal("0.01"))
