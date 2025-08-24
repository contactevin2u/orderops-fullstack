from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Driver, DriverDevice
from ..schemas import DeviceRegisterIn, DriverOut

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
