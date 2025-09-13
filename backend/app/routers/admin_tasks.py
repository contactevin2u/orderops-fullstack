"""Admin task endpoints for maintenance operations"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..services.shift_service import ShiftService
from ..auth.deps import require_roles, Role
from ..db import get_session
from ..utils.responses import envelope

router = APIRouter(prefix="/admin/tasks", tags=["admin-tasks"])
AdminAuth = require_roles(Role.ADMIN)


@router.post("/close-stale-shifts-3am")
def close_stale_shifts_3am(
    db: Session = Depends(get_session),
    _admin = Depends(AdminAuth),
):
    """Close any shifts that have passed their 3AM KL cutoff time"""
    svc = ShiftService(db)
    closed_shifts = svc.close_stale_shifts_3am()
    
    return envelope({
        "ok": True, 
        "closed": len(closed_shifts),
        "shifts": [
            {
                "id": s.id,
                "driver_id": s.driver_id,
                "clock_in_at": s.clock_in_at.isoformat(),
                "clock_out_at": s.clock_out_at.isoformat() if s.clock_out_at else None,
                "closure_reason": s.closure_reason
            }
            for s in closed_shifts
        ]
    })