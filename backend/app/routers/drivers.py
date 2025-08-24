from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Driver, DriverDevice, Trip, Order
from ..schemas import DeviceRegisterIn, DriverOut, DriverOrderOut

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverOut])
def list_drivers(db: Session = Depends(get_session)):
    return db.query(Driver).filter(Driver.is_active == True).all()


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
        .where(Trip.status == "ASSIGNED")
    )
    rows = db.execute(stmt).all()
    return [
        {"id": order.id, "description": order.code, "status": trip.status}
        for trip, order in rows
    ]
