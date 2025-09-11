"""Automated Lorry Assignment Service"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_
import logging
import random
import re

from ..models import (
    Lorry,
    Driver,
    LorryAssignment,
    DriverSchedule,
    User
)

logger = logging.getLogger(__name__)


class LorryAssignmentService:
    """Service for automated lorry assignment management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_lorry(
        self, 
        lorry_id: str,
        plate_number: Optional[str] = None,
        model: Optional[str] = None,
        capacity: Optional[str] = None,
        base_warehouse: str = "BATU_CAVES",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new lorry"""
        try:
            # Check if lorry_id already exists
            existing = self.db.execute(
                select(Lorry).where(Lorry.lorry_id == lorry_id)
            ).scalar_one_or_none()
            
            if existing:
                return {
                    "success": False,
                    "message": f"Lorry with ID {lorry_id} already exists",
                    "lorry": None
                }
            
            # Create new lorry
            lorry = Lorry(
                lorry_id=lorry_id,
                plate_number=plate_number,
                model=model,
                capacity=capacity,
                base_warehouse=base_warehouse,
                notes=notes,
                is_active=True,
                is_available=True
            )
            
            self.db.add(lorry)
            self.db.commit()
            self.db.refresh(lorry)
            
            logger.info(f"Created new lorry: {lorry_id}")
            
            return {
                "success": True,
                "message": f"Successfully created lorry {lorry_id}",
                "lorry": {
                    "id": lorry.id,
                    "lorry_id": lorry.lorry_id,
                    "plate_number": lorry.plate_number,
                    "model": lorry.model,
                    "capacity": lorry.capacity,
                    "base_warehouse": lorry.base_warehouse,
                    "is_active": lorry.is_active,
                    "is_available": lorry.is_available,
                    "notes": lorry.notes,
                    "created_at": lorry.created_at.isoformat()
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating lorry {lorry_id}: {e}")
            return {
                "success": False,
                "message": f"Error creating lorry: {str(e)}",
                "lorry": None
            }
    
    def get_all_lorries(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all lorries"""
        query = select(Lorry)
        
        if not include_inactive:
            query = query.where(Lorry.is_active == True)
        
        lorries = self.db.execute(query.order_by(Lorry.lorry_id)).scalars().all()
        
        return [
            {
                "id": lorry.id,
                "lorry_id": lorry.lorry_id,
                "plate_number": lorry.plate_number,
                "model": lorry.model,
                "capacity": lorry.capacity,
                "base_warehouse": lorry.base_warehouse,
                "is_active": lorry.is_active,
                "is_available": lorry.is_available,
                "notes": lorry.notes,
                "current_location": lorry.current_location,
                "last_maintenance_date": lorry.last_maintenance_date.isoformat() if lorry.last_maintenance_date else None,
                "created_at": lorry.created_at.isoformat(),
                "updated_at": lorry.updated_at.isoformat()
            }
            for lorry in lorries
        ]
    
    def update_driver_priority_lorry(self, driver_id: int, priority_lorry_id: Optional[str]) -> Dict[str, Any]:
        """Update driver's priority lorry"""
        try:
            driver = self.db.get(Driver, driver_id)
            if not driver:
                return {
                    "success": False,
                    "message": f"Driver {driver_id} not found"
                }
            
            # Validate lorry exists if provided
            if priority_lorry_id:
                lorry = self.db.execute(
                    select(Lorry).where(
                        and_(
                            Lorry.lorry_id == priority_lorry_id,
                            Lorry.is_active == True
                        )
                    )
                ).scalar_one_or_none()
                
                if not lorry:
                    return {
                        "success": False,
                        "message": f"Lorry {priority_lorry_id} not found or inactive"
                    }
            
            driver.priority_lorry_id = priority_lorry_id
            self.db.commit()
            
            logger.info(f"Updated driver {driver_id} priority lorry to {priority_lorry_id}")
            
            return {
                "success": True,
                "message": f"Successfully updated driver {driver_id} priority lorry",
                "driver_id": driver_id,
                "priority_lorry_id": priority_lorry_id
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating driver {driver_id} priority lorry: {e}")
            return {
                "success": False,
                "message": f"Error updating priority lorry: {str(e)}"
            }
    
    def auto_assign_lorries_for_date(self, assignment_date: date, admin_user_id: int) -> Dict[str, Any]:
        """Automatically assign lorries to scheduled drivers for a specific date"""
        try:
            logger.info(f"DEBUG: Starting auto-assign for date {assignment_date}")
            
            # Get all scheduled drivers for the date
            scheduled_drivers = self.db.execute(
                select(Driver, DriverSchedule).join(
                    DriverSchedule, Driver.id == DriverSchedule.driver_id
                ).where(
                    and_(
                        DriverSchedule.schedule_date == assignment_date,
                        DriverSchedule.status.in_(["SCHEDULED", "CONFIRMED"]),
                        Driver.is_active == True
                    )
                )
            ).all()
            
            logger.info(f"DEBUG: Found {len(scheduled_drivers)} scheduled drivers for {assignment_date}")
            for driver, schedule in scheduled_drivers:
                logger.info(f"DEBUG: Driver {driver.id} ({driver.name}) - Status: {schedule.status}")
            
            if not scheduled_drivers:
                logger.info(f"DEBUG: No drivers scheduled for {assignment_date}")
                return {
                    "success": True,
                    "message": f"No drivers scheduled for {assignment_date}",
                    "assignments_created": 0,
                    "assignments": []
                }
            
            # Get all available lorries
            available_lorries = self.db.execute(
                select(Lorry).where(
                    and_(
                        Lorry.is_active == True,
                        Lorry.is_available == True
                    )
                ).order_by(Lorry.lorry_id)
            ).scalars().all()
            
            logger.info(f"DEBUG: Found {len(available_lorries)} available lorries")
            for lorry in available_lorries:
                logger.info(f"DEBUG: Available lorry: {lorry.lorry_id} (active={lorry.is_active}, available={lorry.is_available})")
            
            if not available_lorries:
                # Log all lorries to see what's wrong
                all_lorries = self.db.execute(select(Lorry).order_by(Lorry.lorry_id)).scalars().all()
                logger.info(f"DEBUG: No available lorries found. Total lorries in DB: {len(all_lorries)}")
                for lorry in all_lorries:
                    logger.info(f"DEBUG: Lorry {lorry.lorry_id}: is_active={lorry.is_active}, is_available={lorry.is_available}")
                
                return {
                    "success": False,
                    "message": "No available lorries found",
                    "assignments_created": 0,
                    "assignments": []
                }
            
            # Get existing assignments for this date to avoid duplicates
            existing_assignments = self.db.execute(
                select(LorryAssignment).where(
                    LorryAssignment.assignment_date == assignment_date
                )
            ).scalars().all()
            
            assigned_drivers = {assignment.driver_id for assignment in existing_assignments}
            assigned_lorries = {assignment.lorry_id for assignment in existing_assignments}
            
            assignments_created = []
            available_lorry_ids = [lorry.lorry_id for lorry in available_lorries if lorry.lorry_id not in assigned_lorries]
            
            for driver, schedule in scheduled_drivers:
                # Skip if driver already has assignment
                if driver.id in assigned_drivers:
                    logger.info(f"DEBUG: Driver {driver.id} already has assignment for {assignment_date}")
                    continue
                
                logger.info(f"DEBUG: Processing driver {driver.id} ({driver.name}), priority_lorry: {driver.priority_lorry_id}")
                logger.info(f"DEBUG: Available lorries for assignment: {available_lorry_ids}")
                
                # Try to assign priority lorry first
                assigned_lorry_id = None
                
                if driver.priority_lorry_id and driver.priority_lorry_id in available_lorry_ids:
                    assigned_lorry_id = driver.priority_lorry_id
                    logger.info(f"DEBUG: Assigned priority lorry {assigned_lorry_id} to driver {driver.id}")
                else:
                    logger.info(f"DEBUG: Priority lorry {driver.priority_lorry_id} not available, trying pattern matching")
                    # Regex-based automatic assignment (simple pattern matching)
                    assigned_lorry_id = self._find_lorry_by_pattern(driver, available_lorry_ids)
                    
                    # If no pattern match, randomly assign an available lorry
                    if not assigned_lorry_id and available_lorry_ids:
                        assigned_lorry_id = random.choice(available_lorry_ids)
                        logger.info(f"DEBUG: Randomly assigned lorry {assigned_lorry_id} to driver {driver.id}")
                    elif not assigned_lorry_id:
                        logger.warning(f"DEBUG: No lorries available to assign to driver {driver.id}")
                
                if assigned_lorry_id:
                    logger.info(f"DEBUG: Creating assignment - Driver {driver.id} → Lorry {assigned_lorry_id}")
                    # Create assignment
                    assignment = LorryAssignment(
                        driver_id=driver.id,
                        lorry_id=assigned_lorry_id,
                        assignment_date=assignment_date,
                        shift_id=None,  # Will be linked when driver clocks in
                        assigned_by=admin_user_id,
                        status="ASSIGNED",
                        notes=f"Auto-assigned for scheduled shift"
                    )
                    
                    self.db.add(assignment)
                    assignments_created.append({
                        "driver_id": driver.id,
                        "driver_name": driver.name or f"Driver {driver.id}",
                        "lorry_id": assigned_lorry_id,
                        "assignment_type": "priority" if assigned_lorry_id == driver.priority_lorry_id else "auto"
                    })
                    
                    # Remove lorry from available list
                    available_lorry_ids.remove(assigned_lorry_id)
                    assigned_drivers.add(driver.id)
                    logger.info(f"DEBUG: Assignment created successfully")
                else:
                    logger.warning(f"DEBUG: Could not assign lorry to driver {driver.id} - no available lorries")
            
            self.db.commit()
            
            logger.info(f"DEBUG: Auto-assigned {len(assignments_created)} lorries for {assignment_date}")
            logger.info(f"DEBUG: Final assignments created: {assignments_created}")
            
            return {
                "success": True,
                "message": f"Successfully auto-assigned {len(assignments_created)} lorries for {assignment_date}",
                "assignments_created": len(assignments_created),
                "assignments": assignments_created,
                "available_lorries_remaining": len(available_lorry_ids)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in auto-assign for {assignment_date}: {e}")
            return {
                "success": False,
                "message": f"Error during auto-assignment: {str(e)}",
                "assignments_created": 0,
                "assignments": []
            }
    
    def _find_lorry_by_pattern(self, driver: Driver, available_lorry_ids: List[str]) -> Optional[str]:
        """Simple regex pattern matching for lorry assignment"""
        # This is a basic implementation - can be enhanced with more sophisticated rules
        
        # Example patterns:
        # - Driver name starts with 'A' -> prefer lorries starting with 'LRY00A'
        # - Base warehouse matching
        # - Simple alphabetical matching
        
        if not driver.name:
            return None
        
        driver_name_upper = driver.name.upper()
        
        # Pattern 1: Match first letter of driver name
        first_letter = driver_name_upper[0]
        pattern1 = re.compile(f".*{first_letter}.*", re.IGNORECASE)
        
        for lorry_id in available_lorry_ids:
            if pattern1.match(lorry_id):
                logger.info(f"Pattern match: Driver {driver.name} ({first_letter}) -> Lorry {lorry_id}")
                return lorry_id
        
        # Pattern 2: Warehouse-based assignment (future enhancement)
        # This could match lorries typically used at the driver's base warehouse
        
        return None
    
    def get_assignment_status_for_date(self, assignment_date: date) -> Dict[str, Any]:
        """Get assignment status and statistics for a specific date"""
        # Get scheduled drivers
        scheduled_drivers = self.db.execute(
            select(func.count(DriverSchedule.id)).where(
                and_(
                    DriverSchedule.schedule_date == assignment_date,
                    DriverSchedule.status.in_(["SCHEDULED", "CONFIRMED"])
                )
            )
        ).scalar()
        
        # Get assigned drivers
        assigned_drivers = self.db.execute(
            select(func.count(LorryAssignment.id)).where(
                LorryAssignment.assignment_date == assignment_date
            )
        ).scalar()
        
        # Get total available lorries (not assigned for this date)
        assigned_lorry_ids = self.db.execute(
            select(LorryAssignment.lorry_id).where(
                LorryAssignment.assignment_date == assignment_date
            )
        ).scalars().all()
        
        available_lorries = self.db.execute(
            select(func.count(Lorry.id)).where(
                and_(
                    Lorry.is_active == True,
                    Lorry.is_available == True,
                    ~Lorry.lorry_id.in_(assigned_lorry_ids) if assigned_lorry_ids else True
                )
            )
        ).scalar()
        
        # Get assignments for the date
        assignments = self.db.execute(
            select(LorryAssignment, Driver).join(
                Driver, LorryAssignment.driver_id == Driver.id
            ).where(
                LorryAssignment.assignment_date == assignment_date
            ).order_by(LorryAssignment.created_at)
        ).all()
        
        assignment_details = [
            {
                "driver_id": assignment.driver_id,
                "driver_name": driver.name or f"Driver {driver.id}",
                "lorry_id": assignment.lorry_id,
                "status": assignment.status,
                "assigned_at": assignment.assigned_at.isoformat()
            }
            for assignment, driver in assignments
        ]
        
        return {
            "assignment_date": assignment_date.strftime("%Y-%m-%d"),
            "scheduled_drivers": scheduled_drivers or 0,
            "assigned_drivers": assigned_drivers or 0,
            "unassigned_drivers": (scheduled_drivers or 0) - (assigned_drivers or 0),
            "available_lorries": available_lorries or 0,
            "can_auto_assign": (scheduled_drivers or 0) > (assigned_drivers or 0) and (available_lorries or 0) > 0,
            "assignments": assignment_details
        }