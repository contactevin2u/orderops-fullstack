from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from decimal import Decimal
import datetime as dt

from ..auth.firebase import driver_auth, firebase_auth, _get_app
from ..auth.deps import require_roles
from ..db import get_session
from ..models import Driver, DriverDevice, Trip, Order, TripEvent, Role, Commission
from ..schemas import (
    DeviceRegisterIn,
    DriverOut,
    DriverOrderOut,
    DriverOrderUpdateIn,
    DriverCreateIn,
    CommissionMonthOut,
)
from ..utils.storage import save_pod_image

router = APIRouter(prefix="/drivers", tags=["drivers"])

def _order_to_driver_out(order: Order, status: str) -> dict:
    # delivery_date may be datetime or date
    dd = None
    if getattr(order, "delivery_date", None):
        dd = (
            order.delivery_date.date()
            if hasattr(order.delivery_date, "date")
            else order.delivery_date
        )

    items = []
    try:
        for it in getattr(order, "items", []) or []:
            items.append(
                {
                    "id": it.id,
                    "name": it.name,
                    "qty": it.qty,
                    "unit_price": getattr(it, "unit_price", None),
                    "line_total": getattr(it, "line_total", None),
                    "item_type": getattr(it, "item_type", None),
                }
            )
    except Exception:
        items = []

    try:
        cust = getattr(order, "customer", None)
    except Exception:
        cust = None
    customer = None
    if cust:
        customer = {
            "id": cust.id,
            "name": getattr(cust, "name", None),
            "phone": getattr(cust, "phone", None),
            "address": getattr(cust, "address", None),
            "map_url": getattr(cust, "map_url", None),
        }

    return {
        "id": order.id,
        "description": getattr(order, "code", None),
        "code": getattr(order, "code", None),
        "status": status,
        "delivery_date": dd,
        "notes": getattr(order, "notes", None),
        "subtotal": getattr(order, "subtotal", Decimal("0")) or Decimal("0"),
        "discount": getattr(order, "discount", Decimal("0")) or Decimal("0"),
        "delivery_fee": getattr(order, "delivery_fee", Decimal("0")) or Decimal("0"),
        "return_delivery_fee": getattr(order, "return_delivery_fee", Decimal("0")) or Decimal("0"),
        "penalty_fee": getattr(order, "penalty_fee", Decimal("0")) or Decimal("0"),
        "total": getattr(order, "total", Decimal("0")) or Decimal("0"),
        "paid_amount": getattr(order, "paid_amount", Decimal("0")) or Decimal("0"),
        "balance": getattr(order, "balance", Decimal("0")) or Decimal("0"),
        "customer": customer,
        "items": items,
    }


@router.get("", response_model=list[DriverOut])
def list_drivers(db: Session = Depends(get_session)):
    return db.query(Driver).filter(Driver.is_active == True).all()


@router.post("", response_model=DriverOut, dependencies=[Depends(require_roles(Role.ADMIN))])
def create_driver(payload: DriverCreateIn, db: Session = Depends(get_session)):
    try:
        fb_user = firebase_auth.create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.name,
            app=_get_app(),
        )
    except Exception as exc:  # pragma: no cover - network/cred failures
        raise HTTPException(400, "Failed to create driver") from exc
    driver = Driver(firebase_uid=fb_user.uid, name=payload.name, phone=payload.phone)
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.post("/devices")
def register_device(
    payload: DeviceRegisterIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    device = (
        db.query(DriverDevice)
        .filter(
            DriverDevice.driver_id == driver.id,
            DriverDevice.token == payload.token,
        )
        .one_or_none()
    )
    if device:
        device.driver_id = driver.id
        device.platform = payload.platform
        device.app_version = payload.app_version
        device.model = payload.model
    else:
        device = DriverDevice(
            driver_id=driver.id,
            token=payload.token,
            platform=payload.platform,
            app_version=payload.app_version,
            model=payload.model,
        )
        db.add(device)
    db.commit()
    return {"status": "ok"}


@router.get("/orders", response_model=list[DriverOrderOut])
def list_assigned_orders(driver=Depends(driver_auth), db: Session = Depends(get_session)):
    rows = db.execute(
        select(Trip, Order).join(Order, Trip.order_id == Order.id).where(Trip.driver_id == driver.id)
    ).all()
    out = []
    for trip, order in rows:
        out.append(_order_to_driver_out(order, trip.status))
    return out


@router.get("/orders/{order_id}", response_model=DriverOrderOut)
def get_assigned_order(order_id: int, driver=Depends(driver_auth), db: Session = Depends(get_session)):
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_driver_out(order, trip.status)


@router.post("/orders/{order_id}/pod-photo", response_model=dict)
def upload_pod_photo(
    order_id: int,
    file: UploadFile = File(...),
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(404, "Trip not found")
    data = file.file.read()
    try:
        url = save_pod_image(data)
    except Exception as e:  # pragma: no cover - pillow errors
        raise HTTPException(400, str(e)) from e
    trip.pod_photo_url = url
    db.commit()
    db.refresh(trip)
    return {"url": url}


@router.patch("/orders/{order_id}", response_model=DriverOrderOut)
def update_order_status(
    order_id: int,
    payload: DriverOrderUpdateIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(404, "Trip not found")
    if payload.status not in {"IN_TRANSIT", "DELIVERED", "ON_HOLD"}:
        raise HTTPException(400, "Invalid status")
    trip.status = payload.status
    now = datetime.now(timezone.utc)
    if payload.status == "IN_TRANSIT":
        if not trip.started_at:
            trip.started_at = now
    elif payload.status == "DELIVERED":
        if not trip.pod_photo_url:
            raise HTTPException(400, "PoD photo required")
        trip.delivered_at = now
    elif payload.status == "ON_HOLD":
        pass
    db.add(TripEvent(trip_id=trip.id, status=payload.status))
    order = db.get(Order, order_id)
    db.commit()
    return _order_to_driver_out(order, trip.status)


@router.get("/commissions", response_model=list[CommissionMonthOut])
def my_commissions(
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    month_expr = (
        func.strftime("%Y-%m", Commission.created_at)
        if db.bind.dialect.name == "sqlite"
        else func.to_char(Commission.created_at, "YYYY-MM")
    )
    stmt = (
        select(month_expr.label("month"), func.sum(Commission.computed_amount).label("total"))
        .where(Commission.driver_id == driver.id)
        .group_by("month")
        .order_by("month")
    )
    rows = db.execute(stmt).all()
    return [
        {"month": row.month, "total": float(row.total or 0)}
        for row in rows
    ]


@router.get(
    "/{driver_id}/commissions",
    response_model=list[CommissionMonthOut],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def driver_commissions(driver_id: int, db: Session = Depends(get_session)):
    month_expr = (
        func.strftime("%Y-%m", Commission.created_at)
        if db.bind.dialect.name == "sqlite"
        else func.to_char(Commission.created_at, "YYYY-MM")
    )
    stmt = (
        select(month_expr.label("month"), func.sum(Commission.computed_amount).label("total"))
        .where(Commission.driver_id == driver_id)
        .group_by("month")
        .order_by("month")
    )
    rows = db.execute(stmt).all()
    return [
        {"month": row.month, "total": float(row.total or 0)}
        for row in rows
    ]
