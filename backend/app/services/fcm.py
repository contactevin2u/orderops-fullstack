import json
import os
from typing import Any, Dict

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from ..models import Driver, Order

_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
_credentials = None
_project_id = None


def _get_access_token() -> tuple[str, str]:
    global _credentials, _project_id
    if _credentials is None:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON not set")
        info = json.loads(raw)
        _project_id = info.get("project_id")
        _credentials = service_account.Credentials.from_service_account_info(
            info, scopes=_SCOPES
        )
    request = Request()
    token = _credentials.with_scopes(_SCOPES)
    token.refresh(request)
    return token.token, _project_id


def send_to_token(token: str, title: str, body: str, data: Dict[str, Any]) -> None:
    try:
        access_token, project_id = _get_access_token()
    except Exception:
        return
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    message = {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": data,
            "android": {
                "priority": "HIGH",
                "notification": {"channel_id": "orders_high"},
            },
        }
    }
    try:
        httpx.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=message,
            timeout=10,
        ).raise_for_status()
    except Exception:
        # Silently ignore notification errors
        pass


def notify_order_assigned(db: Session, driver_id: int, order: Order) -> None:
    driver = db.get(Driver, driver_id)
    if not driver:
        return
    title = "New Order Assigned"
    body = f"Order #{getattr(order, 'code', '')}"
    data = {
        "type": "ORDER_ASSIGNED",
        "order_id": str(getattr(order, 'id', '')),
        "code": getattr(order, "code", ""),
        "pickup_address": getattr(order, "pickup_address", ""),
        "dropoff_address": getattr(order, "dropoff_address", ""),
        "delivery_window": getattr(order, "delivery_window", ""),
    }
    for device in driver.devices:
        send_to_token(device.token, title, body, data)
