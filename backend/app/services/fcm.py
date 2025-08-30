import json
import os
import logging
from typing import Any, Dict

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from ..core.push import PUSH_ANDROID_CHANNEL_ID
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


def send_to_token(
    token: str,
    title: str,
    body: str,
    data: Dict[str, Any],
    channel_id: str | None = None,
) -> tuple[int, str]:
    access_token, project_id = _get_access_token()
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    message = {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": data,
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": channel_id or PUSH_ANDROID_CHANNEL_ID
                },
            },
        }
    }
    hdrs = {"Authorization": f"Bearer {access_token}"}
    resp = httpx.post(url, headers=hdrs, json=message, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        logging.exception(
            "FCM send failed",
            extra={
                "status": getattr(resp, "status_code", None),
                "body": getattr(resp, "text", None),
            },
        )
        raise
    return resp.status_code, resp.text


def notify_order_assigned(db: Session, driver_id: int, order: Order) -> None:
    driver = db.get(Driver, driver_id)
    if not driver:
        return
    title = "New Order Assigned"
    body = f"Order #{getattr(order, 'code', '')}"
    data = {
        "type": "job_assigned",
        "jobId": str(getattr(order, 'id', '')),
        "order_id": str(getattr(order, 'id', '')),
        "code": getattr(order, "code", ""),
        "pickup_address": getattr(order, "pickup_address", ""),
        "dropoff_address": getattr(order, "dropoff_address", ""),
        "delivery_window": getattr(order, "delivery_window", ""),
    }
    for device in driver.devices:
        try:
            send_to_token(device.token, title, body, data)
        except Exception:
            logging.exception(
                "notify_order_assigned push failed",
                extra={"driver_id": driver_id, "token": device.token},
            )
