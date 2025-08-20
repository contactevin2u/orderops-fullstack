from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from ..models import Plan


def months_elapsed(start: datetime | None, end: datetime | None = None) -> int:
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
