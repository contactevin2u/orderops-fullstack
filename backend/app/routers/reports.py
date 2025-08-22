from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Order, Payment
from ..services.plan_math import months_elapsed


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/outstanding", response_model=dict)
def outstanding(
    order_type: str = Query(default="ALL", alias="type"),
    as_of: date | None = Query(default=None),
    exclude_cleared: bool = Query(default=True),
    db: Session = Depends(get_session),
):
    """Return outstanding balances for orders as of ``as_of`` date."""

    as_of = as_of or date.today()
    end_dt = datetime.combine(as_of, datetime.min.time())
    rows = db.query(Order).all()
    items: list[dict] = []

    for o in rows:
        if order_type and order_type != "ALL" and o.type != order_type:
            continue
        if not o.delivery_date or o.delivery_date.date() > as_of:
            continue

        if exclude_cleared:
            if o.status == "RETURNED":
                continue
            if o.status == "CANCELLED" and (o.penalty_fee or 0) > 0:
                continue

        expected = Decimal("0.00")
        months = months_elapsed(o.delivery_date, end_dt)
        for it in o.items:
            t = (it.item_type or "").upper()
            if t == "OUTRIGHT":
                price = it.line_total or (it.unit_price or 0) * (it.qty or 0)
                expected += Decimal(str(price))
            elif t in {"INSTALLMENT", "RENTAL"}:
                monthly = Decimal(str(it.unit_price or it.line_total or 0))
                m = months
                if (
                    t == "INSTALLMENT"
                    and getattr(o, "plan", None)
                    and o.plan.months  # noqa: E501
                ):
                    try:
                        m = min(m, int(o.plan.months))
                    except Exception:
                        pass
                expected += monthly * Decimal(m)
            # FEE or other items ignored here

        fees = Decimal(
            str(
                (o.delivery_fee or 0)
                + (o.return_delivery_fee or 0)
                + (o.penalty_fee or 0)
            )
        )

        paid = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.order_id == o.id)
            .filter(Payment.status == "POSTED")
            .filter(Payment.date <= as_of)
            .scalar()
        )
        paid = Decimal(str(paid))

        bal = (expected + fees - paid).quantize(Decimal("0.01"))
        if bal <= 0:
            continue

        items.append(
            {
                "id": o.id,
                "code": o.code,
                "customer": {"name": getattr(o.customer, "name", "")},
                "type": o.type,
                "status": o.status,
                "expected": float(expected),
                "paid": float(paid),
                "fees": float(fees),
                "balance": float(bal),
            }
        )

    totals = {
        k: float(sum(Decimal(str(it[k])) for it in items))
        for k in ("expected", "paid", "fees", "balance")
    }
    return {"as_of": str(as_of), "items": items, "totals": totals}
