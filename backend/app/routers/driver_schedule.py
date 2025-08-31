"""Driver schedule management endpoints"""

from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.deps import require_roles
from ..models.user import Role
from ..db import get_session
from ..services.driver_schedule_service import DriverScheduleService
from ..utils.responses import envelope


router = APIRouter(prefix="/driver-schedule", tags=["driver-schedule"])


class WeeklyScheduleRequest(BaseModel):
    driver_id: int
    weekdays: List[bool]  # [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
    pattern_name: Optional[str] = None
    start_date: Optional[date] = None


class DailyScheduleRequest(BaseModel):
    driver_id: int
    schedule_date: date
    is_scheduled: bool = True
    shift_type: str = "FULL_DAY"
    notes: Optional[str] = None


@router.get("/weekly/{start_date}")
def get_weekly_schedule(
    start_date: date,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Get weekly schedule starting from given date"""
    schedule_service = DriverScheduleService(db)
    weekly_schedule = schedule_service.get_weekly_schedule(start_date)
    return envelope({"weekly_schedule": weekly_schedule})


@router.get("/date/{schedule_date}")
def get_daily_schedule(
    schedule_date: date,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Get drivers scheduled for specific date"""
    schedule_service = DriverScheduleService(db)
    scheduled_drivers = schedule_service.get_scheduled_drivers_for_date(schedule_date)
    summary = schedule_service.get_schedule_summary(schedule_date)
    
    return envelope({
        "scheduled_drivers": scheduled_drivers,
        "summary": summary
    })


@router.post("/weekly-pattern")
def create_weekly_pattern(
    request: WeeklyScheduleRequest,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Create recurring weekly availability pattern for driver"""
    schedule_service = DriverScheduleService(db)
    
    pattern = schedule_service.create_availability_pattern(
        driver_id=request.driver_id,
        weekdays=request.weekdays,
        pattern_name=request.pattern_name,
        start_date=request.start_date
    )
    
    return envelope({
        "pattern_id": pattern.id,
        "driver_id": pattern.driver_id,
        "pattern_name": pattern.pattern_name,
        "weekdays": [
            pattern.monday, pattern.tuesday, pattern.wednesday, pattern.thursday,
            pattern.friday, pattern.saturday, pattern.sunday
        ]
    })


@router.post("/daily-override")
def set_daily_schedule(
    request: DailyScheduleRequest,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Set explicit schedule for driver on specific date (overrides pattern)"""
    schedule_service = DriverScheduleService(db)
    
    schedule = schedule_service.set_daily_schedule(
        driver_id=request.driver_id,
        schedule_date=request.schedule_date,
        is_scheduled=request.is_scheduled,
        shift_type=request.shift_type,
        notes=request.notes
    )
    
    return envelope({
        "schedule_id": schedule.id,
        "driver_id": schedule.driver_id,
        "schedule_date": schedule.schedule_date.isoformat(),
        "is_scheduled": schedule.is_scheduled,
        "status": schedule.status
    })


@router.get("/drivers/all")
def get_all_drivers_with_schedule(
    target_date: Optional[date] = None,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Get all drivers with their schedule status for given date"""
    if target_date is None:
        target_date = date.today()
        
    schedule_service = DriverScheduleService(db)
    scheduled_drivers = schedule_service.get_scheduled_drivers_for_date(target_date)
    
    # Get all active drivers
    from ..models.driver import Driver
    all_drivers = db.query(Driver).filter(Driver.is_active == True).all()
    
    scheduled_ids = {d["driver_id"] for d in scheduled_drivers}
    
    drivers_with_schedule = []
    for driver in all_drivers:
        is_scheduled = driver.id in scheduled_ids
        schedule_info = next((d for d in scheduled_drivers if d["driver_id"] == driver.id), None)
        
        drivers_with_schedule.append({
            "driver_id": driver.id,
            "driver_name": driver.name,
            "phone": driver.phone,
            "is_scheduled": is_scheduled,
            "schedule_type": schedule_info.get("schedule_type") if schedule_info else None,
            "shift_type": schedule_info.get("shift_type") if schedule_info else None,
            "status": schedule_info.get("status") if schedule_info else None
        })
    
    return envelope({
        "date": target_date.isoformat(),
        "drivers": drivers_with_schedule,
        "scheduled_count": len(scheduled_drivers),
        "total_count": len(all_drivers)
    })


@router.put("/driver/{driver_id}/status")
def update_driver_status(
    driver_id: int,
    status: str,  # CONFIRMED, CALLED_SICK, NO_SHOW
    schedule_date: Optional[date] = None,
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Update driver status for specific date"""
    if schedule_date is None:
        schedule_date = date.today()
        
    schedule_service = DriverScheduleService(db)
    schedule_service.mark_driver_status(driver_id, schedule_date, status)
    
    return envelope({
        "driver_id": driver_id,
        "status": status,
        "schedule_date": schedule_date.isoformat()
    })