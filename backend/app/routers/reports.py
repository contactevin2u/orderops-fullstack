from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session, selectinload

from ..auth.deps import require_roles
from ..db import get_session
from ..models import Order, Role
from ..reports.outstanding import compute_expected_for_order
from ..services.ordersvc import _sum_posted_payments, q2

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("/outstanding", response_model=dict)
def outstanding(
    order_type: str = Query(default="ALL", alias="type"),
    as_of: date | None = Query(default=None),
    exclude_cleared: bool = Query(default=True),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    as_of = as_of or date.today()
    query = (
        db.query(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
            selectinload(Order.plan),
            selectinload(Order.payments),
            selectinload(Order.adjustments).selectinload(Order.payments),
        )
        .filter(Order.delivery_date != None)
        .filter(Order.delivery_date <= as_of)
    )
    if order_type and order_type != "ALL":
        query = query.filter(Order.type == order_type)
    if exclude_cleared:
        query = query.filter(Order.status != "RETURNED")
        query = query.filter(~and_(Order.status == "CANCELLED", (Order.penalty_fee == None) | (Order.penalty_fee <= 0)))
    orders = query.order_by(Order.id).offset(offset).limit(limit).all()

    items: list[dict] = []
    totals = {"expected": Decimal("0"), "paid": Decimal("0"), "fees": Decimal("0"), "balance": Decimal("0")}
    for order in orders:
        expected = compute_expected_for_order(order, as_of)
        fees = q2((order.delivery_fee or 0) + (order.return_delivery_fee or 0) + (order.penalty_fee or 0))
        paid = _sum_posted_payments(order) + sum(
            (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []), Decimal("0")
        )
        balance = q2(expected - paid)
        if balance <= 0:
            continue
        items.append(
            {
                "id": order.id,
                "code": order.code,
                "customer": {"name": order.customer.name if order.customer else None},
                "type": order.type,
                "status": order.status,
                "expected": float(expected),
                "paid": float(paid),
                "fees": float(fees),
                "balance": float(balance),
            }
        )
        totals["expected"] += expected
        totals["paid"] += paid
        totals["fees"] += fees
        totals["balance"] += balance

    totals = {k: float(q2(v)) for k, v in totals.items()}
    return {"as_of": str(as_of), "items": items, "totals": totals}
