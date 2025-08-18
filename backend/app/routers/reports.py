from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from ..db import get_session
from ..models import Order

router = APIRouter(prefix="/reports", tags=["reports"])

def months_elapsed(start: datetime, end: datetime | None = None) -> int:
    if not isinstance(start, datetime):
        return 0
    end = end or datetime.utcnow()
    y = end.year - start.year
    m = end.month - start.month
    d = end.day - start.day
    return max(y * 12 + m + (1 if d >= 0 else 0), 0)

@router.get("/outstanding", response_model=dict)
def outstanding(type: str | None = Query(default=None), db: Session = Depends(get_session)):
    rows = db.query(Order).all()
    out = {"INSTALLMENT": [], "RENTAL": []}
    for o in rows:
        if type and o.type != type:
            continue
        if not o.delivery_date:
            continue

        plan = o.plan
        if o.type in ("INSTALLMENT", "RENTAL") and plan:
            months = months_elapsed(o.delivery_date)
            expected = Decimal(str(plan.monthly_amount)) * Decimal(months)
        else:
            months = 0
            expected = Decimal("0.00")

        paid = o.paid_amount or Decimal("0.00")
        add_fees = (o.delivery_fee or 0) + (o.return_delivery_fee or 0) + (o.penalty_fee or 0)
        bal = (expected + Decimal(str(add_fees)) - paid).quantize(Decimal("0.01"))

        if o.type in out:
            out[o.type].append({
                "order_id": o.id,
                "code": o.code,
                "customer": getattr(o.customer, "name", ""),
                "months_elapsed": months,
                "monthly_amount": str(getattr(plan, "monthly_amount", "0.00")) if plan else "0.00",
                "paid": str(paid),
                "balance_computed": str(bal),
                "status": o.status,
            })
    return out
