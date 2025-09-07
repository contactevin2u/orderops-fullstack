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
        # compact JSON string, hard-limit to column size
        details_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if len(details_str) > 255:
            details_str = details_str[:252] + "..."
        db.add(AuditLog(user_id=user_id, action=action, details=details_str))
        db.commit()
    except Exception:
        db.rollback()
        # Never let audit failures break primary flows
        return


