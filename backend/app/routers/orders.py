from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date

from ..db import get_session
from ..models import Order, OrderItem, Plan, Customer, IdempotentRequest
from ..schemas import OrderOut
from ..services.ordersvc import create_order_from_parsed
from ..services.plan_math import calculate_plan_due
from ..services.status_updates import (
    apply_buyback,
    cancel_installment,
    mark_cancelled,
    mark_returned,
    recompute_financials,
)
from ..utils.responses import envelope

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=dict)
def list_orders(
    q: str | None = None,
    status: str | None = None,
    type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
):
    stmt = select(Order, Customer.name.label("customer_name")).join(
        Customer, Customer.id == Order.customer_id
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Order.code.ilike(like), Customer.name.ilike(like)))
    if status:
        stmt = stmt.where(Order.status == status)
    if type:
        stmt = stmt.where(Order.type == type)
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    out: list[OrderListOut] = []
    for (order, customer_name) in rows:
        dto = OrderOut.model_validate(order).model_dump()
        dto["customer_name"] = customer_name
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
    id: int
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

@router.post("", response_model=dict, status_code=201)
def create_order(
    body: ManualOrderIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
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


@router.get("/{order_id}/due", response_model=dict)
def get_order_due(order_id: int, as_of: date | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    as_of = as_of or date.today()
    paid = order.paid_amount or Decimal("0.00")
    fees = (
        (order.delivery_fee or Decimal("0.00"))
        + (order.return_delivery_fee or Decimal("0.00"))
        + (order.penalty_fee or Decimal("0.00"))
    )
    if order.status in {"CANCELLED", "RETURNED"} or (
        order.plan and order.plan.status != "ACTIVE"
    ):
        expected = fees
    elif order.type in ("INSTALLMENT", "RENTAL") and order.plan:
        expected = calculate_plan_due(order.plan, as_of) + fees
    else:
        expected = order.total or Decimal("0.00")

    balance = (expected - paid).quantize(Decimal("0.01"))

    return envelope({
        "expected": float(expected),
        "paid": float(paid),
        "balance": float(balance),
    })


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

    if "items" in data:
        for ip in data["items"]:
            iid = ip.get("id")
            if not iid:
                continue
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


    # Recompute monetary totals based on current state
    recompute_financials(order)
    db.commit()
    db.refresh(order)
    return envelope(OrderOut.model_validate(order))


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
            date.fromisoformat(body.date) if body and body.date else None,
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
