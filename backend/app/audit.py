from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .core.push import PUSH_ANDROID_CHANNEL_ID
from .db import get_session
from .models.driver import DriverDevice
from .services.fcm import _get_access_token, send_to_token

router = APIRouter(prefix="/_audit", tags=["audit"])


@router.get("/routes")
def audit_routes(request: Request) -> list[Dict[str, Any]]:
    routes: list[Dict[str, Any]] = []
    for r in request.app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if path and methods:
            routes.append({"path": path, "methods": sorted(list(methods))})
    return routes


@router.get("/db")
def audit_db(driver_id: int | None = None, db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        result: Dict[str, Any] = {"ok": True}
        if driver_id is not None:
            q = (
                select(DriverDevice.token)
                .where(DriverDevice.driver_id == driver_id)
                .order_by(DriverDevice.id.desc())
                .limit(10)
            )
            result["tokens"] = db.execute(q).scalars().all()
        return result
    except Exception as e:  # pragma: no cover - audit helper
        return {"ok": False, "reason": str(e)}


@router.get("/fcm")
def audit_fcm() -> Dict[str, Any]:
    try:
        access_token, project_id = _get_access_token()
        return {
            "ok": True,
            "project_id": project_id,
            "access_token_len": len(access_token),
        }
    except Exception as e:  # pragma: no cover - audit helper
        return {"ok": False, "reason": str(e)}


@router.post("/push")
def audit_push(payload: Dict[str, Any]) -> Dict[str, Any]:
    token = payload.get("token")
    title = payload.get("title") or ""
    body = payload.get("body") or ""
    data = payload.get("data") or {}
    channel = payload.get("channel_id") or PUSH_ANDROID_CHANNEL_ID
    try:
        status, resp_body = send_to_token(token, title, body, data, channel)
        return {"ok": True, "status": status, "body": resp_body}
    except Exception as e:  # pragma: no cover - audit helper
        return {"ok": False, "reason": str(e)}
