from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import DriverDevice, Trip
from ..schemas import DeviceRegisterIn
from ..services.notifications import notify_trip_assignment

router = APIRouter(prefix="/drivers", tags=["drivers"])


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


@router.post("/{driver_id}/notify", response_model=dict)
def resend_trip_notification(driver_id: int, trip_id: int, db: Session = Depends(get_session)):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_id != driver_id:
        raise HTTPException(404, "Trip not found")
    count = notify_trip_assignment(db, trip)
    return {"sent": count}
