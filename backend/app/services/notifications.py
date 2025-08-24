from __future__ import annotations

from firebase_admin import messaging
from sqlalchemy.orm import Session

from ..auth.firebase import _get_app
from ..models import DriverDevice, Trip


def notify_trip_assignment(db: Session, trip: Trip) -> int:
    """Send an FCM notification to all devices for the trip's driver."""
    tokens = [
        d.fcm_token
        for d in db.query(DriverDevice).filter(DriverDevice.driver_id == trip.driver_id)
    ]
    if not tokens:
        return 0
    try:
        app = _get_app()
        message = messaging.MulticastMessage(
            tokens=tokens,
            data={
                "type": "trip_assignment",
                "trip_id": str(trip.id),
                "order_id": str(trip.order_id),
            },
        )
        resp = messaging.send_multicast(message, app=app)
        return resp.success_count
    except Exception:  # pragma: no cover - best effort only
        return 0
