import json
import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Driver, User, Role
from ..core.security import hash_password

firebase_app = None
security = HTTPBearer()


def _get_app():
    global firebase_app
    if firebase_app is None:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON not set")
        cred = credentials.Certificate(json.loads(raw))
        firebase_app = firebase_admin.initialize_app(cred)
    return firebase_app


def verify_firebase_id_token(id_token: str) -> Dict[str, Any]:
    app = _get_app()
    return firebase_auth.verify_id_token(id_token, app=app)


def driver_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> Driver:
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    try:
        claims = verify_firebase_id_token(credentials.credentials)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    firebase_uid = claims["uid"]
    phone = claims.get("phone_number")
    name = claims.get("name")
    driver = db.query(Driver).filter(Driver.firebase_uid == firebase_uid).one_or_none()
    if not driver:
        driver = Driver(firebase_uid=firebase_uid, phone=phone, name=name)
        db.add(driver)
        db.commit()
        db.refresh(driver)
    try:
        user = db.query(User).filter(User.username == firebase_uid).one_or_none()
        if not user:
            user = User(
                username=firebase_uid,
                password_hash=hash_password(firebase_uid),
                role=Role.DRIVER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        request.state.user = user
    except Exception:  # pragma: no cover - user table may not exist
        request.state.user = None
    request.state.driver = driver
    return driver
