from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Driver, DriverDevice

router = APIRouter(prefix="/driver", tags=["driver"])


@router.get("/me")
def get_me(driver=Depends(driver_auth)):
    """Get current driver information - Firebase authenticated"""
    return {
        "id": driver.id,
        "name": driver.name,
        "phone": driver.phone,
        "firebase_uid": driver.firebase_uid,
        "role": "driver"
    }


class PushTokenIn(BaseModel):
    token: str


@router.post("/push-tokens")
def register_push_token(
    payload: PushTokenIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Register or update FCM push token for driver"""
    device = (
        db.query(DriverDevice)
        .filter(
            DriverDevice.driver_id == driver.id,
            DriverDevice.token == payload.token,
        )
        .one_or_none()
    )
    
    if device:
        # Token already exists, update timestamp
        device.driver_id = driver.id
    else:
        # Create new device entry
        device = DriverDevice(
            driver_id=driver.id,
            token=payload.token,
            platform="android",  # Default to android since this is from driver app
            app_version="unknown",
            model="unknown",
        )
        db.add(device)
    
    db.commit()
    return {"status": "ok", "message": "Push token registered successfully"}