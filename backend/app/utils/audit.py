from __future__ import annotations
import json
from typing import Any, Optional
from sqlalchemy.orm import Session

from ..models import AuditLog, User


def log_action(
    db: Session,
    user_id: Optional[int] = None,
    action: str = "",
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Any = None,
) -> None:
    """
    Record an audit log. Never raise to the caller.
    - details may be dict/any -> stored as JSON string truncated to 255 chars
    - resource_* are embedded into details JSON for traceability
    """
    try:
        payload = {"resource_type": resource_type, "resource_id": resource_id, "details": details}
        # Store as dict object - PostgreSQL JSON column will handle serialization
        db.add(AuditLog(user_id=user_id, action=action, details=payload))
        db.commit()
    except Exception:
        db.rollback()
        # Never let audit failures break primary flows
        return


