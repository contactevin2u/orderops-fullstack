from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from ..db import get_session
from ..models import Order
from ..services.plan_math import calculate_plan_due

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/outstanding", response_model=dict)
def outstanding(type: str | None = Query(default=None), db: Session = Depends(get_session)):
    """Return outstanding balances for orders.

    The payload is normalized to ``{"items": [...]}`` where each item contains
    ``id``, ``code``, ``customer`` (object with ``name``), ``type``, ``status``
    and ``balance``.  An optional ``type`` query parameter can be supplied to
    filter by order type.
    """

    today = datetime.utcnow().date()
    rows = db.query(Order).all()
    items: list[dict] = []

    for o in rows:
        if type and o.type != type:
            continue
        if not o.delivery_date:
            continue

        paid = Decimal(o.paid_amount or 0)

        if o.type in ("INSTALLMENT", "RENTAL") and o.plan:
            # Amount expected to be paid as of today plus any additional fees
            expected = calculate_plan_due(o.plan, today)
            fees = (o.delivery_fee or 0) + (o.return_delivery_fee or 0) + (o.penalty_fee or 0)
            expected += Decimal(str(fees))
        else:
            # For outright and other orders rely on stored total
            expected = Decimal(o.total or 0)

        bal = (expected - paid).quantize(Decimal("0.01"))

        items.append(
            {
                "id": o.id,
                "code": o.code,
                "customer": {"name": getattr(o.customer, "name", "")},
                "type": o.type,
                "status": o.status,
                "balance": float(bal),
            }
        )

    return {"items": items}
