"""Deep trace debug endpoints"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db import get_session
from ..models.driver import Driver
from ..models.driver_shift import DriverShift  
from ..models.driver_schedule import DriverSchedule
from ..utils.responses import envelope

router = APIRouter(prefix="/debug-trace", tags=["debug-trace"])

@router.get("/assignment-step-by-step")
def trace_assignment_logic(db: Session = Depends(get_session)):
    """Step-by-step trace of assignment service logic"""
    try:
        today = date.today()
        
        # Step 1: Check what schedules exist
        all_schedules = db.query(DriverSchedule).all()
        schedule_data = []
        for s in all_schedules:
            schedule_data.append({
                "driver_id": s.driver_id,
                "schedule_date": s.schedule_date.isoformat(),
                "is_scheduled": s.is_scheduled,
                "matches_today": s.schedule_date == today
            })
        
        # Step 2: Filter schedules for today exactly
        today_schedules = (
            db.query(DriverSchedule)
            .filter(
                and_(
                    DriverSchedule.schedule_date == today,
                    DriverSchedule.is_scheduled == True
                )
            )
            .all()
        )
        
        today_schedule_data = []
        scheduled_ids = set()
        for s in today_schedules:
            today_schedule_data.append({
                "driver_id": s.driver_id,
                "schedule_date": s.schedule_date.isoformat(),
                "is_scheduled": s.is_scheduled
            })
            scheduled_ids.add(s.driver_id)
        
        # Step 3: Get active shifts
        active_shifts = db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        shift_data = []
        clocked_in_ids = set()
        for s in active_shifts:
            shift_data.append({
                "driver_id": s.driver_id,
                "status": s.status,
                "clock_in_at": s.clock_in_at.isoformat() if s.clock_in_at else None
            })
            clocked_in_ids.add(s.driver_id)
        
        # Step 4: Get all active drivers
        all_drivers = db.query(Driver).filter(Driver.is_active == True).all()
        all_driver_data = []
        for d in all_drivers:
            all_driver_data.append({
                "id": d.id,
                "name": d.name,
                "is_active": d.is_active,
                "is_scheduled_today": d.id in scheduled_ids,
                "is_clocked_in": d.id in clocked_in_ids
            })
        
        # Step 5: Filter drivers by scheduled IDs (this is the critical step)
        scheduled_drivers = (
            db.query(Driver)
            .filter(
                and_(
                    Driver.is_active == True,
                    Driver.id.in_(scheduled_ids)
                )
            )
            .all()
        ) if scheduled_ids else []
        
        final_driver_data = []
        for d in scheduled_drivers:
            is_clocked_in = d.id in clocked_in_ids
            priority = 1 if is_clocked_in else 2
            final_driver_data.append({
                "driver_id": d.id,
                "driver_name": d.name,
                "is_clocked_in": is_clocked_in,
                "is_scheduled": True,
                "priority": priority
            })
        
        return envelope({
            "today": today.isoformat(),
            "step1_all_schedules": {
                "count": len(all_schedules),
                "schedules": schedule_data
            },
            "step2_today_schedules": {
                "count": len(today_schedules),
                "schedules": today_schedule_data,
                "scheduled_driver_ids": list(scheduled_ids)
            },
            "step3_active_shifts": {
                "count": len(active_shifts),
                "shifts": shift_data,
                "clocked_in_driver_ids": list(clocked_in_ids)
            },
            "step4_all_active_drivers": {
                "count": len(all_drivers),
                "drivers": all_driver_data
            },
            "step5_final_available_drivers": {
                "count": len(scheduled_drivers),
                "drivers": final_driver_data
            },
            "expected_result": "Should only show drivers 2 and 3 if logic is correct"
        })
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })