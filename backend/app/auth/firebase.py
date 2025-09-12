import json
import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
    # Ensure session is in clean state
    if db.in_transaction():
        try:
            db.commit()
        except Exception:
            db.rollback()

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
        try:
            driver = Driver(firebase_uid=firebase_uid, phone=phone, name=name)
            db.add(driver)
            db.commit()
            db.refresh(driver)
        except IntegrityError as e:
            db.rollback()
            # Check if driver was created by another request (race condition)
            driver = (
                db.query(Driver)
                .filter(Driver.firebase_uid == firebase_uid)
                .one_or_none()
            )
            if not driver:
                # If still no driver after rollback, re-raise the original error
                raise e
    try:
        user = db.query(User).filter(User.username == firebase_uid).one_or_none()
        if not user:
            try:
                user = User(
                    username=firebase_uid,
                    password_hash=hash_password(firebase_uid),
                    role=Role.DRIVER,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            except IntegrityError as e:
                db.rollback()
                # Check if user was created by another request (race condition)
                user = (
                    db.query(User).filter(User.username == firebase_uid).one_or_none()
                )
                if not user:
                    # If still no user after rollback, re-raise the original error
                    raise e
        request.state.user = user
    except Exception:  # pragma: no cover - user table may not exist
        db.rollback()
        request.state.user = None
    request.state.driver = driver
    return driver


def get_current_driver(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> Driver:
    """Get current authenticated driver"""
    return driver_auth(request, credentials, db)


def admin_firebase_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    """Firebase authentication for admin users (email/password based)"""
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    try:
        claims = verify_firebase_id_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from exc

    firebase_uid = claims["uid"]
    email = claims.get("email")
    name = claims.get("name")

    # Check if this Firebase user should be an admin
    admin_emails = os.environ.get("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip().lower() for email in admin_emails if email.strip()]

    if email and email.lower() not in admin_emails:
        raise HTTPException(status_code=403, detail="Not authorized as admin")

    # Find or create admin user
    user = db.query(User).filter(User.username == firebase_uid).one_or_none()
    if not user:
        try:
            # Create admin user from Firebase
            user = User(
                username=firebase_uid,
                password_hash=hash_password(firebase_uid),  # Dummy password hash
                role=Role.ADMIN,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError as e:
            db.rollback()
            # Check if user was created by another request (race condition)
            user = db.query(User).filter(User.username == firebase_uid).one_or_none()
            if not user:
                # If still no user after rollback, re-raise the original error
                raise HTTPException(
                    status_code=500, detail=f"Failed to create admin user: {str(e)}"
                )

    # Ensure user is admin
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="User is not an admin")

    request.state.user = user
    return user


def get_current_admin_user(
    request: Request,
    token: str | None = Cookie(default=None, alias="token"),
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_session),
) -> User:
    """Get current admin user - supports both web cookies and Firebase tokens"""

    # Ensure session is in clean state
    if db.in_transaction():
        try:
            db.commit()
        except Exception:
            db.rollback()

    # Try web authentication first (cookie-based)
    if token:
        try:
            from ..core.security import decode_access_token

            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)
                user = db.get(User, user_id)
                if user and user.role == Role.ADMIN:
                    request.state.user = user
                    return user
        except Exception:
            pass  # Fall through to Firebase auth

    # Try Firebase authentication (mobile app)
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            claims = verify_firebase_id_token(credentials.credentials)
            firebase_uid = claims["uid"]
            email = claims.get("email")

            # Check if this Firebase user should be an admin
            admin_emails = os.environ.get("ADMIN_EMAILS", "").split(",")
            admin_emails = [e.strip().lower() for e in admin_emails if e.strip()]

            # If no admin emails configured, allow any Firebase user to be admin (dev mode)
            is_admin_email = not admin_emails or (
                email and email.lower() in admin_emails
            )

            if is_admin_email:
                # Find or create admin user
                user = (
                    db.query(User).filter(User.username == firebase_uid).one_or_none()
                )
                if not user:
                    try:
                        user = User(
                            username=firebase_uid,
                            password_hash=hash_password(firebase_uid),
                            role=Role.ADMIN,
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
                    except IntegrityError:
                        db.rollback()
                        # Check if user was created by another request (race condition)
                        user = (
                            db.query(User)
                            .filter(User.username == firebase_uid)
                            .one_or_none()
                        )
                        if not user:
                            # If still no user after rollback, fall through to error
                            pass

                # Ensure user is admin
                if user and user.role == Role.ADMIN:
                    request.state.user = user
                    return user

        except Exception as exc:
            pass  # Fall through to error

    # If no valid authentication found
    raise HTTPException(status_code=401, detail="Admin authentication required")
