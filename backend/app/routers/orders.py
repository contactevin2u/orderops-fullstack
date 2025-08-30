from fastapi import APIRouter, Depends, HTTPException, Query, Header, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date as date_cls, time, timedelta, timezone
from zoneinfo import ZoneInfo

from ..db import get_session
from ..models import (
    Order,
    OrderItem,
    Plan,
    Customer,
    IdempotentRequest,
    Role,
    User,
    Driver,
    Trip,
    Commission,
)
from ..auth.deps import require_roles
from ..utils.audit import log_action
from ..schemas import OrderOut, AssignDriverIn
from ..services.ordersvc import (
    create_order_from_parsed,
    recompute_financials,
    _sum_posted_payments,
    q2,
    ensure_plan_first_month_fee,
)
from ..reports.outstanding import compute_expected_for_order, calculate_plan_due
from ..services.status_updates import (
    apply_buyback,
    cancel_installment,
    mark_cancelled,
    mark_returned,
)
from ..services.documents import invoice_pdf
from ..utils.responses import envelope
from ..utils.normalize import to_decimal
from ..services.fcm import notify_order_assigned

APP_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def kl_day_bounds(d: datetime | date_cls):
    """Return (start_utc, end_utc) for KL local day covering date d."""
    if isinstance(d, datetime):
        d = d.date()
    start_local = datetime.combine(d, time.min, tzinfo=APP_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def kl_month_bounds(year: int, month: int):
    """Return (start_utc, end_utc) for KL local month."""
    start_local = datetime(year, month, 1, tzinfo=APP_TZ)
    end_local = (start_local.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=dict)
def list_orders(
    q: str | None = None,
    status: str | None = None,
    type: str | None = None,
    date: str | None = None,
    unassigned: bool = False,
    driver_id: int | None = None,
    month: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
):
    stmt = (
        select(
            Order,
            Customer.name.label("customer_name"),
            Trip,
            Driver.name.label("driver_name"),
            Commission,
        )
        .join(Customer, Customer.id == Order.customer_id)
        .join(Trip, Trip.order_id == Order.id, isouter=True)
        .join(Driver, Driver.id == Trip.driver_id, isouter=True)
        .join(Commission, Commission.trip_id == Trip.id, isouter=True)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Order.code.ilike(like), Customer.name.ilike(like), Customer.phone.ilike(like))
        )
    if status:
        stmt = stmt.where(Order.status == status)
    if type:
        stmt = stmt.where(Order.type == type)

    if driver_id is not None:
        stmt = stmt.where(Trip.driver_id == driver_id)

    if month:
        try:
            y, m = map(int, month.split("-"))
            start_utc, end_utc = kl_month_bounds(y, m)
            stmt = stmt.where(
                and_(Order.delivery_date >= start_utc, Order.delivery_date < end_utc)
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid month format (expected YYYY-MM)")

    # --- Date filtering (backlog semantics) ---
    if date:
        try:
            d = datetime.fromisoformat(date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)")

        start_utc, end_utc = kl_day_bounds(d)

        backlog_mode = (unassigned is True) or (status == "ON_HOLD")

        if backlog_mode:
            stmt = stmt.where(
                or_(
                    Order.delivery_date.is_(None),
                    Order.delivery_date < end_utc,
                )
            )
        else:
            stmt = stmt.where(
                and_(
                    Order.delivery_date >= start_utc,
                    Order.delivery_date < end_utc,
                )
            )

    if unassigned:
        # No trip or trip has no route yet (still not assigned to a route)
        stmt = stmt.where(and_(or_(Trip.id.is_(None), Trip.route_id.is_(None))))
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    out: list[OrderListOut] = []
    for (order, customer_name, trip, driver_name, commission) in rows:
        dto = OrderOut.model_validate(order).model_dump()
        dto["customer_name"] = customer_name
        if trip:
            trip_dto = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "status": trip.status,
                "driver_name": driver_name,
                "route_id": trip.route_id,
                "pod_photo_url": trip.pod_photo_url,  # Kept for backward compatibility
                "pod_photo_urls": trip.pod_photo_urls,
            }
            if commission:
                trip_dto["commission"] = {
                    "id": commission.id,
                    "scheme": commission.scheme,
                    "rate": commission.rate,
                    "computed_amount": commission.computed_amount,
                    "actualized_at": commission.actualized_at,
                }
            dto["trip"] = trip_dto
        out.append(OrderListOut.model_validate(dto))
    return envelope(out)

class ManualOrderIn(BaseModel):
    customer: dict
    order: dict


class PlanPatch(BaseModel):
    plan_type: str | None = None
    months: int | None = None
    monthly_amount: float | None = None
    status: str | None = None
    start_date: str | None = None


class OrderItemPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    item_type: str | None = None
    sku: str | None = None
    category: str | None = None
    qty: int | None = None
    unit_price: float | None = None
    line_total: float | None = None


class OrderPatch(BaseModel):
    notes: str | None = None
    status: str | None = None
    delivery_date: str | None = None
    subtotal: float | None = None
    discount: float | None = None
    delivery_fee: float | None = None
    return_delivery_fee: float | None = None
    penalty_fee: float | None = None
    total: float | None = None
    balance: float | None = None
    plan: PlanPatch | None = None
    items: list[OrderItemPatch] | None = None
    delete_items: list[int] | None = None

@router.post("", response_model=dict, status_code=201)
def create_order(
    body: ManualOrderIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    try:
        if idempotency_key:
            existing = db.query(Order).filter_by(idempotency_key=idempotency_key).one_or_none()
            if existing:
                return envelope(OrderOut.model_validate(existing))
        order = create_order_from_parsed(db, {"customer": body.customer, "order": body.order})
        if idempotency_key:
            order.idempotency_key = idempotency_key
        db.commit()
        db.refresh(order)
        log_action(db, current_user, "order.create", f"order_id={order.id}")
        return envelope(OrderOut.model_validate(order))
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Create failed: {e}")

@router.get("/{order_id}", response_model=dict)
def get_order(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return envelope(OrderOut.model_validate(order))


@router.get("/{order_id}/invoice.pdf")
def get_invoice_pdf(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    pdf = invoice_pdf(order)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice_{order.code}.pdf"'},
    )


@router.get("/{order_id}/due", response_model=dict)
def get_order_due(order_id: int, as_of: date_cls | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    as_of = as_of or date_cls.today()

    expected = compute_expected_for_order(order, as_of)
    paid = _sum_posted_payments(order) + sum(
        (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []),
        Decimal("0"),
    )
    balance = q2(expected - paid)
    to_collect = q2(balance if balance > 0 else Decimal("0"))
    to_refund = q2(-balance if balance < 0 else Decimal("0"))
    accrued = calculate_plan_due(order.plan, as_of)

    return envelope(
        {
            "expected": float(expected),
            "paid": float(paid),
            "balance": float(balance),
            "to_collect": float(to_collect),
            "to_refund": float(to_refund),
            "accrued": float(accrued),
        }
    )


@router.patch("/{order_id}", response_model=dict)
def update_order(order_id: int, body: OrderPatch, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    data = body.model_dump(exclude_none=True)

    for k in ["notes", "status", "delivery_date"]:
        if k in data:
            setattr(order, k, data[k])

    money_fields = [
        "subtotal",
        "discount",
        "delivery_fee",
        "return_delivery_fee",
        "penalty_fee",
        "total",
        "balance",
    ]
    for k in money_fields:
        if k in data:
            setattr(order, k, Decimal(str(data[k])))

    if "plan" in data and order.plan:
        plan_patch = data["plan"]
        if "monthly_amount" in plan_patch:
            order.plan.monthly_amount = Decimal(str(plan_patch["monthly_amount"]))
        for k in ["plan_type", "months", "status"]:
            if k in plan_patch:
                setattr(order.plan, k, plan_patch[k])
        if plan_patch.get("start_date"):
            try:
                order.plan.start_date = datetime.fromisoformat(plan_patch["start_date"]).date()
            except Exception:
                pass

    if "delete_items" in data:
        for iid in data["delete_items"]:
            item = next((it for it in order.items if it.id == iid), None)
            if item:
                order.items.remove(item)
                db.delete(item)

    if "items" in data:
        for ip in data["items"]:
            iid = ip.get("id")
            if iid:
                item = next((it for it in order.items if it.id == iid), None)
                if not item:
                    continue
                for k in ["name", "item_type", "sku", "category"]:
                    if k in ip:
                        setattr(item, k, ip[k])
                if "qty" in ip:
                    item.qty = int(ip["qty"])
                for k in ["unit_price", "line_total"]:
                    if k in ip:
                        setattr(item, k, Decimal(str(ip[k])))
            else:
                name = (ip.get("name") or "").strip() or "Item"
                item_type = (ip.get("item_type") or "OUTRIGHT").strip().upper()
                sku = ip.get("sku")
                category = ip.get("category")
                qty = int(ip.get("qty") or 0)
                unit_price = Decimal(str(ip.get("unit_price") or 0))
                lt_input = ip.get("line_total")
                line_total = Decimal(str(lt_input)) if lt_input is not None else unit_price * qty
                if item_type in {"RENTAL", "INSTALLMENT"}:
                    if lt_input is not None and Decimal(str(lt_input)) > 0:
                        raise HTTPException(400, "Plan items cannot have positive totals")
                    if line_total >= 0:
                        unit_price = Decimal("0")
                        line_total = Decimal("0")
                order.items.append(
                    OrderItem(
                        name=name,
                        item_type=item_type,
                        sku=sku,
                        category=category,
                        qty=qty,
                        unit_price=unit_price,
                        line_total=line_total,
                    )
                )


    # Recompute monetary totals based on current state
    if order.plan:
        ensure_plan_first_month_fee(order)
    else:
        recompute_financials(order)
    db.commit()
    db.refresh(order)
    return envelope(OrderOut.model_validate(order))


@router.post("/{order_id}/assign", response_model=dict)
def assign_order(
    order_id: int,
    body: AssignDriverIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    driver = db.get(Driver, body.driver_id)
    if not driver:
        raise HTTPException(404, "Driver not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if trip:
        if trip.status in {"DELIVERED", "SUCCESS"}:
            raise HTTPException(400, "Delivered orders cannot be reassigned")
        trip.driver_id = driver.id
        trip.status = "ASSIGNED"
    else:
        trip = Trip(order_id=order.id, driver_id=driver.id, status="ASSIGNED")
        db.add(trip)
    db.commit()
    db.refresh(trip)
    log_action(db, current_user, "order.assign_driver", f"order_id={order.id},driver_id={driver.id}")
    notify_order_assigned(db, driver.id, order)
    return envelope({"order_id": order.id, "driver_id": driver.id, "trip_id": trip.id})


class CommissionUpdateIn(BaseModel):
    amount: Decimal


@router.post("/{order_id}/success", response_model=dict)
def mark_success(
    order_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if not trip or trip.status != "DELIVERED":
        raise HTTPException(400, "Trip not delivered")
    total = to_decimal(order.total or 0)
    if total < 500:
        rate = Decimal("20")
    elif total < 5000:
        rate = Decimal("30")
    else:
        rate = Decimal("50")
    commission = db.query(Commission).filter_by(trip_id=trip.id).one_or_none()
    now = datetime.utcnow()
    if commission:
        commission.rate = rate
        commission.computed_amount = rate
        commission.actualized_at = now
        commission.actualization_reason = "manual_success"
    else:
        commission = Commission(
            driver_id=trip.driver_id,
            trip_id=trip.id,
            scheme="FLAT",
            rate=rate,
            computed_amount=rate,
            actualized_at=now,
            actualization_reason="manual_success",
        )
        db.add(commission)
    trip.status = "SUCCESS"
    db.commit()
    db.refresh(commission)
    log_action(db, current_user, "order.success", f"order_id={order.id}")
    return envelope({"commission_id": commission.id, "amount": float(commission.computed_amount)})


@router.patch("/{order_id}/commission", response_model=dict)
def update_commission(
    order_id: int,
    body: CommissionUpdateIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")
    commission = db.query(Commission).filter_by(trip_id=trip.id).one_or_none()
    amt = to_decimal(body.amount)
    if commission:
        commission.rate = amt
        commission.computed_amount = amt
    else:
        commission = Commission(
            driver_id=trip.driver_id,
            trip_id=trip.id,
            scheme="FLAT",
            rate=amt,
            computed_amount=amt,
        )
        db.add(commission)
    db.commit()
    db.refresh(commission)
    log_action(db, current_user, "commission.update", f"commission_id={commission.id}")
    return envelope({"commission_id": commission.id, "amount": float(commission.computed_amount)})


@router.post("/{order_id}/void", response_model=dict)
def void_order(
    order_id: int,
    body: dict | None = None,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope({"order_id": order.id, "status": order.status})

    reason = (body or {}).get("reason") if body else None
    try:
        mark_cancelled(db, order, reason)
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="void"))
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope({"order_id": order.id, "status": order.status})


class ReturnIn(BaseModel):
    date: str | None = None
    return_delivery_fee: Decimal | None = None
    collect: bool | None = False
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/return", response_model=dict)
def return_order(
    order_id: int,
    body: ReturnIn | None = None,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    ret_date = None
    if body and body.date:
        try:
            ret_date = datetime.fromisoformat(body.date)
        except Exception:
            ret_date = None
    try:
        mark_returned(
            db,
            order,
            ret_date,
            body.return_delivery_fee if body else None,
            bool(body.collect) if body else False,
            body.method if body else None,
            body.reference if body else None,
            date_cls.fromisoformat(body.date) if body and body.date else None,
        )
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="return"))
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))


class DiscountIn(BaseModel):
    type: str
    value: Decimal


class BuybackIn(BaseModel):
    amount: Decimal
    discount: DiscountIn | None = None
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/buyback", response_model=dict)
def buyback_order(
    order_id: int,
    body: BuybackIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    try:
        discount = body.discount.model_dump() if body.discount else None
        apply_buyback(
            db,
            order,
            Decimal(str(body.amount)),
            discount,
            body.method,
            body.reference,
        )
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="buyback"))
        db.commit()
        db.refresh(order)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))


class CancelInstallmentIn(BaseModel):
    penalty: Decimal | None = None
    return_delivery_fee: Decimal | None = None
    collect: bool | None = False
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/cancel-installment", response_model=dict)
def cancel_installment_order(
    order_id: int,
    body: CancelInstallmentIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    try:
        cancel_installment(
            db,
            order,
            body.penalty,
            body.return_delivery_fee,
            bool(body.collect) if body.collect is not None else False,
            body.method,
            body.reference,
        )
        db.add(
            IdempotentRequest(key=idempotency_key, order_id=order.id, action="cancel_installment")
        )
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))
