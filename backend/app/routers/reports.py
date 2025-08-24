from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, and_, cast, case, func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Customer, Order, OrderItem, Payment, Plan, Role
from ..auth.deps import require_roles
from ..services.plan_math import months_elapsed


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
    """Return outstanding balances for orders as of ``as_of`` date."""

    as_of = as_of or date.today()
    end_dt = datetime.combine(as_of, datetime.min.time())

    paid_subq = (
        select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.order_id == Order.id,
                Payment.status == "POSTED",
                Payment.date <= as_of,
            )
            .correlate(Order)
            .scalar_subquery()
    )

    days_elapsed_expr = func.DATE_PART("day", as_of - Order.delivery_date)
    months_elapsed_expr = cast(days_elapsed_expr / 30.0, Integer)
    months_expr = case(
        (Plan.months != None, func.least(Plan.months, months_elapsed_expr)),
        else_=months_elapsed_expr,
    )

    outright_expr = func.coalesce(
        func.sum(
            case(
                (OrderItem.item_type == "OUTRIGHT",
                 func.coalesce(OrderItem.line_total, OrderItem.unit_price * OrderItem.qty)),
                else_=0,
            )
        ),
        0,
    )
    monthly_expr = func.coalesce(
        func.sum(
            case(
                (OrderItem.item_type.in_(["INSTALLMENT", "RENTAL"]),
                 func.coalesce(OrderItem.unit_price, OrderItem.line_total, 0)),
                else_=0,
            )
        ),
        0,
    )

    expected_expr = case(
        (Order.status == "CANCELLED", 0),
        else_=outright_expr + monthly_expr * months_expr,
    )
    fees_expr = (
        func.coalesce(Order.delivery_fee, 0)
        + func.coalesce(Order.return_delivery_fee, 0)
        + func.coalesce(Order.penalty_fee, 0)
    )
    balance_expr = expected_expr + fees_expr - paid_subq

    stmt = (
        select(
            Order.id,
            Order.code,
            Order.type,
            Order.status,
            Customer.name.label("customer_name"),
            expected_expr.label("expected"),
            fees_expr.label("fees"),
            paid_subq.label("paid"),
            balance_expr.label("balance"),
        )
        .join(Customer, Customer.id == Order.customer_id)
        .outerjoin(OrderItem, OrderItem.order_id == Order.id)
        .outerjoin(Plan, Plan.order_id == Order.id)
        .where(Order.delivery_date != None)
        .where(Order.delivery_date <= as_of)
    )

    if order_type and order_type != "ALL":
        stmt = stmt.where(Order.type == order_type)

    if exclude_cleared:
        stmt = stmt.where(Order.status != "RETURNED")
        stmt = stmt.where(
            ~and_(
                Order.status == "CANCELLED",
                func.coalesce(Order.penalty_fee, 0) <= 0,
            )
        )

    stmt = stmt.group_by(
        Order.id,
        Order.code,
        Order.type,
        Order.status,
        Customer.name,
        Order.delivery_fee,
        Order.return_delivery_fee,
        Order.penalty_fee,
        Plan.months,
        Order.delivery_date,
    )
    stmt = stmt.order_by(balance_expr.desc()).limit(limit).offset(offset)

    rows = db.execute(stmt).all()
    items: list[dict] = []
    for row in rows:
        expected = Decimal(str(row.expected or 0))
        fees = Decimal(str(row.fees or 0))
        paid = Decimal(str(row.paid or 0))
        bal = (expected + fees - paid).quantize(Decimal("0.01"))

        if row.type == "MIXED":  # Fallback for complex cases
            o = db.get(Order, row.id)
            months = months_elapsed(o.delivery_date, end_dt)
            expected = Decimal("0")
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
                        and o.plan.months
                    ):
                        try:
                            m = min(m, int(o.plan.months))
                        except Exception:
                            pass
                    expected += monthly * Decimal(m)
            bal = (expected + fees - paid).quantize(Decimal("0.01"))

        if bal <= 0:
            continue

        items.append(
            {
                "id": row.id,
                "code": row.code,
                "customer": {"name": row.customer_name},
                "type": row.type,
                "status": row.status,
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

