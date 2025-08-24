from sqlalchemy.orm import Session

from ..models import AuditLog, User


def log_action(db: Session, user: User | None, action: str, details: str | None = None) -> None:
    try:
        db.add(AuditLog(user_id=user.id if user else None, action=action, details=details))
        db.commit()
    except Exception:  # pragma: no cover - audit table may not exist
        db.rollback()


