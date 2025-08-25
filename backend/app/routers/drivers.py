from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.firebase import driver_auth, firebase_auth, _get_app
from ..auth.deps import require_roles
from ..db import get_session
from ..models import Driver, DriverDevice, Trip, Order, TripEvent, Role
from ..schemas import (
    DeviceRegisterIn,
    DriverOut,
    DriverOrderOut,
    DriverOrderUpdateIn,
    DriverCreateIn,
)

router = APIRouter(prefix="/drivers", tags=["drivers"])


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


@router.post("/devices/register")
def register_device(
    payload: DeviceRegisterIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    device = (
        db.query(DriverDevice)
        .filter(
            DriverDevice.driver_id == driver.id,
            DriverDevice.fcm_token == payload.fcm_token,
        )
        .one_or_none()
    )
    if device:
        device.platform = payload.platform
    else:
        device = DriverDevice(
            driver_id=driver.id,
            fcm_token=payload.fcm_token,
            platform=payload.platform,
        )
        db.add(device)
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok"}


@router.get("/orders", response_model=list[DriverOrderOut])
def list_assigned_orders(
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    stmt = (
        select(Trip, Order)
        .join(Order, Trip.order_id == Order.id)
        .where(Trip.driver_id == driver.id)
    )
    rows = db.execute(stmt).all()
    results = []
    for trip, order in rows:
        try:
            items = [
                {"id": item.id, "name": item.name, "qty": item.qty}
                for item in order.items
            ]
        except Exception:
            items = []
        results.append(
            {
                "id": order.id,
                "description": order.code,
                "status": trip.status,
                "items": items,
            }
        )
    return results


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
        trip.delivered_at = now
    elif payload.status == "ON_HOLD":
        pass
    db.add(TripEvent(trip_id=trip.id, status=payload.status))
    order = db.get(Order, order_id)
    db.commit()
    try:
        items = [
            {"id": item.id, "name": item.name, "qty": item.qty}
            for item in order.items
        ]
    except Exception:
        items = []
    return {
        "id": order.id,
        "description": order.code,
        "status": trip.status,
        "items": items,
    }
