from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import User, Role, AuditLog
from ..core.security import verify_password, create_access_token, hash_password
from ..auth.deps import get_current_user
from ..core.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str
    remember: bool | None = False


class RegisterIn(BaseModel):
    username: str
    password: str
    role: Role | None = None


@router.post("/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    expire = timedelta(days=7) if payload.remember else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": str(user.id), "role": user.role.value}, expire)
    max_age = int(expire.total_seconds()) if payload.remember else None
    response.set_cookie(
        "token",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
    )
    db.add(AuditLog(user_id=user.id, action="login"))
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role.value}


@router.post("/register")
def register(
    payload: RegisterIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        count = db.query(User).count()
    except Exception:  # pragma: no cover - tables may not exist yet
        User.__table__.create(bind=db.get_bind(), checkfirst=True)
        AuditLog.__table__.create(bind=db.get_bind(), checkfirst=True)
        count = 0
    if count > 0 and current_user.role != Role.ADMIN:
        raise HTTPException(403, "Forbidden")
    role = payload.role or (Role.ADMIN if count == 0 else Role.CASHIER)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.add(
        AuditLog(
            user_id=None if count == 0 else current_user.id,
            action="create_user",
            details=payload.username,
        )
    )
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role.value}


@router.post("/logout")
def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    response.delete_cookie("token")
    db.add(AuditLog(user_id=current_user.id, action="logout"))
    db.commit()
    return {"ok": True}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role.value}

