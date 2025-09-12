from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import User, Role
from ..core.security import decode_access_token


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Cookie(default=None, alias="token"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_session),
) -> User:
    raw_token = token
    if credentials:
        raw_token = credentials.credentials
    if not raw_token:
        # Allow open access when user table not present or empty (tests/initial setup)
        try:
            count = db.query(User).count()
        except Exception:  # pragma: no cover - table may not exist
            count = 0
        if count == 0:
            dummy = User(id=0, username="anon", password_hash="", role=Role.ADMIN)  # type: ignore
            request.state.user = dummy
            return dummy
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_access_token(raw_token)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(401, "Invalid token") from exc
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(401, "Invalid token: missing user ID")
    user_id = int(user_id_str)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    request.state.user = user
    return user


def require_roles(*roles: Role):
    def _require(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(403, "Forbidden")
        return user

    return _require


def admin_auth(user: User = Depends(get_current_user)) -> User:
    """Admin authentication dependency"""
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required"
        )
    return user

