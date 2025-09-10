"""Driver schedule management service"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.driver import Driver
from app.models.driver_schedule import DriverSchedule, DriverAvailabilityPattern

logger = logging.getLogger(__name__)


class DriverScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def get_scheduled_drivers_for_date(self, schedule_date: date) -> List[Dict[str, Any]]:
        """
        Get drivers scheduled to work on a specific date
        
        Args:
            schedule_date: Date to check schedules for
            
        Returns:
            List of driver information for scheduled drivers
        """
        # First check for explicit daily schedules
        explicit_schedules = self.db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.schedule_date == schedule_date,
                DriverSchedule.is_scheduled == True,
                DriverSchedule.status.in_(["SCHEDULED", "CONFIRMED"])
            )
        ).all()
        
        scheduled_driver_ids = {schedule.driver_id for schedule in explicit_schedules}
        
        # Then check availability patterns for drivers not explicitly scheduled
        weekday = schedule_date.weekday()  # 0=Monday, 6=Sunday
        
        # Get active patterns for the date
        pattern_query = self.db.query(DriverAvailabilityPattern).filter(
            and_(
                DriverAvailabilityPattern.is_active == True,
                DriverAvailabilityPattern.start_date <= schedule_date,
                or_(
                    DriverAvailabilityPattern.end_date == None,
                    DriverAvailabilityPattern.end_date >= schedule_date
                )
            )
        )
        
        # Filter by weekday
        weekday_filters = {
            0: DriverAvailabilityPattern.monday == True,
            1: DriverAvailabilityPattern.tuesday == True,
            2: DriverAvailabilityPattern.wednesday == True,
            3: DriverAvailabilityPattern.thursday == True,
            4: DriverAvailabilityPattern.friday == True,
            5: DriverAvailabilityPattern.saturday == True,
            6: DriverAvailabilityPattern.sunday == True,
        }
        
        if weekday in weekday_filters:
            pattern_query = pattern_query.filter(weekday_filters[weekday])
        
        patterns = pattern_query.all()
        
        # Add drivers from patterns (if not already explicitly scheduled)
        for pattern in patterns:
            if pattern.driver_id not in scheduled_driver_ids:
                scheduled_driver_ids.add(pattern.driver_id)
        
        # Get full driver information
        if not scheduled_driver_ids:
            return []
        
        drivers = self.db.query(Driver).filter(
            and_(
                Driver.id.in_(scheduled_driver_ids),
                Driver.is_active == True
            )
        ).all()
        
        scheduled_drivers = []
        for driver in drivers:
            # Get specific schedule info if exists
            explicit_schedule = next(
                (s for s in explicit_schedules if s.driver_id == driver.id), 
                None
            )
            
            # Get pattern info if no explicit schedule
            pattern = None
            if not explicit_schedule:
                pattern = next(
                    (p for p in patterns if p.driver_id == driver.id),
                    None
                )
            
            scheduled_drivers.append({
                "driver_id": driver.id,
                "driver_name": driver.name or "Unknown Driver",
                "phone": driver.phone,
                "schedule_type": "explicit" if explicit_schedule else "pattern",
                "shift_type": explicit_schedule.shift_type if explicit_schedule else "FULL_DAY",
                "status": explicit_schedule.status if explicit_schedule else "SCHEDULED",
                "pattern_name": pattern.pattern_name if pattern else None,
                "notes": explicit_schedule.notes if explicit_schedule else None
            })
        
        return scheduled_drivers

    def get_weekly_schedule(self, start_date: date) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get full week schedule starting from given date
        
        Args:
            start_date: Start of the week
            
        Returns:
            Dictionary with date strings as keys and driver lists as values
        """
        weekly_schedule = {}
        
        for i in range(7):  # 7 days
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            scheduled_drivers = self.get_scheduled_drivers_for_date(current_date)
            weekly_schedule[date_str] = scheduled_drivers
        
        return weekly_schedule

    def create_availability_pattern(
        self, 
        driver_id: int, 
        weekdays: List[bool],  # [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
        pattern_name: str = None,
        start_date: date = None
    ) -> DriverAvailabilityPattern:
        """
        Create a recurring availability pattern for a driver
        
        Args:
            driver_id: Driver ID
            weekdays: List of 7 booleans for each day of week
            pattern_name: Optional name for the pattern
            start_date: When pattern starts (defaults to today)
        """
        if len(weekdays) != 7:
            raise ValueError("weekdays must be a list of 7 boolean values")
        
        if start_date is None:
            start_date = date.today()
        
        # Deactivate existing patterns for this driver
        self.db.query(DriverAvailabilityPattern).filter(
            DriverAvailabilityPattern.driver_id == driver_id
        ).update({"is_active": False})
        
        pattern = DriverAvailabilityPattern(
            driver_id=driver_id,
            monday=weekdays[0],
            tuesday=weekdays[1],
            wednesday=weekdays[2],
            thursday=weekdays[3],
            friday=weekdays[4],
            saturday=weekdays[5],
            sunday=weekdays[6],
            pattern_name=pattern_name,
            start_date=start_date,
            is_active=True
        )
        
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        
        return pattern

    def set_daily_schedule(
        self,
        driver_id: int,
        schedule_date: date,
        is_scheduled: bool = True,
        shift_type: str = "FULL_DAY",
        notes: str = None,
        admin_user_id: Optional[int] = None
    ) -> DriverSchedule:
        """
        Set explicit schedule for a driver on a specific date
        (overrides pattern for that date)
        """
        # Check if schedule already exists
        existing = self.db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.driver_id == driver_id,
                DriverSchedule.schedule_date == schedule_date
            )
        ).first()
        
        was_scheduled_before = existing.is_scheduled if existing else False
        
        if existing:
            existing.is_scheduled = is_scheduled
            existing.shift_type = shift_type
            existing.notes = notes
            existing.status = "SCHEDULED" if is_scheduled else "UNSCHEDULED"
            existing.updated_at = datetime.utcnow()
            schedule = existing
        else:
            schedule = DriverSchedule(
                driver_id=driver_id,
                schedule_date=schedule_date,
                is_scheduled=is_scheduled,
                shift_type=shift_type,
                notes=notes,
                status="SCHEDULED" if is_scheduled else "UNSCHEDULED"
            )
            self.db.add(schedule)
        
        self.db.commit()
        self.db.refresh(schedule)
        
        # Trigger lorry assignment/reassignment if schedule changed
        if is_scheduled != was_scheduled_before and admin_user_id:
            self._trigger_lorry_assignment(schedule_date, admin_user_id, 
                                         driver_id, is_scheduled)
        
        return schedule

    def mark_driver_status(
        self,
        driver_id: int,
        schedule_date: date,
        status: str  # CONFIRMED, CALLED_SICK, NO_SHOW
    ):
        """Update driver status for a specific date"""
        schedule = self.db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.driver_id == driver_id,
                DriverSchedule.schedule_date == schedule_date
            )
        ).first()
        
        if not schedule:
            # Create schedule entry if it doesn't exist
            schedule = DriverSchedule(
                driver_id=driver_id,
                schedule_date=schedule_date,
                is_scheduled=True,
                status=status
            )
            self.db.add(schedule)
        else:
            schedule.status = status
            schedule.updated_at = datetime.utcnow()
        
        self.db.commit()

    def get_expected_drivers_count(self, target_date: date = None) -> int:
        """
        Get count of drivers expected to work on given date
        Used by AI service for better planning
        """
        if target_date is None:
            target_date = date.today()
        
        scheduled_drivers = self.get_scheduled_drivers_for_date(target_date)
        return len(scheduled_drivers)

    def get_schedule_summary(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get comprehensive schedule summary for a date
        """
        if target_date is None:
            target_date = date.today()
        
        scheduled_drivers = self.get_scheduled_drivers_for_date(target_date)
        
        # Count by status
        status_counts = {}
        shift_type_counts = {}
        
        for driver in scheduled_drivers:
            status = driver["status"]
            shift_type = driver["shift_type"]
            
            status_counts[status] = status_counts.get(status, 0) + 1
            shift_type_counts[shift_type] = shift_type_counts.get(shift_type, 0) + 1
        
        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_scheduled": len(scheduled_drivers),
            "drivers": scheduled_drivers,
            "status_breakdown": status_counts,
            "shift_type_breakdown": shift_type_counts,
            "weekday": target_date.strftime("%A")
        }

    def _trigger_lorry_assignment(
        self, 
        schedule_date: date, 
        admin_user_id: int, 
        driver_id: int, 
        is_scheduled: bool
    ):
        """
        Trigger automatic lorry assignment/reassignment when driver schedule changes
        """
        try:
            from app.services.lorry_assignment_service import LorryAssignmentService
            from app.models.lorry_assignment import LorryAssignment
            
            lorry_service = LorryAssignmentService(self.db)
            
            if is_scheduled:
                # Driver was scheduled - attempt to assign a lorry
                logger.info(f"Driver {driver_id} scheduled for {schedule_date}, triggering lorry assignment")
                
                # Check if driver already has assignment
                existing_assignment = self.db.query(LorryAssignment).filter(
                    and_(
                        LorryAssignment.driver_id == driver_id,
                        LorryAssignment.assignment_date == schedule_date
                    )
                ).first()
                
                if not existing_assignment:
                    # Auto-assign for this specific driver
                    result = self._assign_single_driver(driver_id, schedule_date, admin_user_id)
                    logger.info(f"Lorry assignment result for driver {driver_id}: {result}")
                else:
                    logger.info(f"Driver {driver_id} already has lorry assignment for {schedule_date}")
            
            else:
                # Driver was unscheduled - remove lorry assignment
                logger.info(f"Driver {driver_id} unscheduled for {schedule_date}, removing lorry assignment")
                
                assignment = self.db.query(LorryAssignment).filter(
                    and_(
                        LorryAssignment.driver_id == driver_id,
                        LorryAssignment.assignment_date == schedule_date
                    )
                ).first()
                
                if assignment:
                    # Cancel the assignment
                    assignment.status = "CANCELLED"
                    assignment.notes = f"{assignment.notes or ''} - Driver unscheduled".strip()
                    self.db.commit()
                    
                    logger.info(f"Cancelled lorry assignment for unscheduled driver {driver_id}")
                    
                    # Trigger reassignment for remaining scheduled drivers
                    self._trigger_reassignment_for_date(schedule_date, admin_user_id)
                
        except Exception as e:
            logger.error(f"Error triggering lorry assignment for driver {driver_id}: {e}")
            # Don't raise - schedule operation should still succeed
    
    def _assign_single_driver(self, driver_id: int, schedule_date: date, admin_user_id: int) -> Dict[str, Any]:
        """
        Assign a lorry to a single scheduled driver
        """
        try:
            from app.services.lorry_assignment_service import LorryAssignmentService
            from app.models.lorry import Lorry
            from app.models.lorry_assignment import LorryAssignment
            
            # Get the driver
            driver = self.db.query(Driver).filter(Driver.id == driver_id).first()
            if not driver:
                return {"success": False, "message": "Driver not found"}
            
            # Get available lorries
            assigned_lorries = self.db.query(LorryAssignment.lorry_id).filter(
                LorryAssignment.assignment_date == schedule_date
            ).subquery()
            
            available_lorries = self.db.query(Lorry).filter(
                and_(
                    Lorry.is_active == True,
                    Lorry.is_available == True,
                    ~Lorry.lorry_id.in_(assigned_lorries)
                )
            ).all()
            
            if not available_lorries:
                return {"success": False, "message": "No available lorries"}
            
            # Try priority lorry first
            assigned_lorry_id = None
            if driver.priority_lorry_id:
                priority_lorry = next(
                    (l for l in available_lorries if l.lorry_id == driver.priority_lorry_id), 
                    None
                )
                if priority_lorry:
                    assigned_lorry_id = priority_lorry.lorry_id
            
            # Fall back to first available lorry
            if not assigned_lorry_id:
                assigned_lorry_id = available_lorries[0].lorry_id
            
            # Create assignment
            assignment = LorryAssignment(
                driver_id=driver_id,
                lorry_id=assigned_lorry_id,
                assignment_date=schedule_date,
                assigned_by=admin_user_id,
                status="ASSIGNED",
                notes="Auto-assigned when driver was scheduled"
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Assigned lorry {assigned_lorry_id} to driver {driver_id}",
                "lorry_id": assigned_lorry_id
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error assigning single driver {driver_id}: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def _trigger_reassignment_for_date(self, schedule_date: date, admin_user_id: int):
        """
        Trigger reassignment for all scheduled drivers on a date
        (when a driver is unscheduled and their lorry becomes available)
        """
        try:
            from app.services.lorry_assignment_service import LorryAssignmentService
            
            lorry_service = LorryAssignmentService(self.db)
            result = lorry_service.auto_assign_lorries_for_date(schedule_date, admin_user_id)
            
            logger.info(f"Triggered reassignment for {schedule_date}: {result}")
            
        except Exception as e:
            logger.error(f"Error triggering reassignment for {schedule_date}: {e}")