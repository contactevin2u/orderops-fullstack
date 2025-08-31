"""Auto-logout service for drivers after clock-out"""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.driver_shift import DriverShift
from app.models.driver import Driver
from app.utils.geofencing import get_location_description

logger = logging.getLogger(__name__)


class AutoLogoutService:
    def __init__(self, db: Session):
        self.db = db

    def process_clock_out_logout(self, shift: DriverShift) -> dict:
        """
        Process auto-logout after driver clocks out
        
        Args:
            shift: Completed DriverShift record
            
        Returns:
            Dictionary with logout status and message
        """
        if shift.status != "COMPLETED":
            return {
                "logout_required": False,
                "message": "Shift not completed"
            }

        driver = self.db.query(Driver).filter(Driver.id == shift.driver_id).first()
        if not driver:
            return {
                "logout_required": False,
                "message": "Driver not found"
            }

        # Generate location-based message
        location_message = self._generate_location_message(shift)
        
        # Generate shift summary message
        summary_message = self._generate_shift_summary_message(shift)

        return {
            "logout_required": True,
            "driver_id": driver.id,
            "driver_name": driver.name,
            "shift_summary": summary_message,
            "location_message": location_message,
            "total_working_hours": shift.total_working_hours,
            "outstation_allowance": shift.outstation_allowance_amount,
            "message": f"Shift completed! {summary_message} {location_message}"
        }

    def _generate_location_message(self, shift: DriverShift) -> str:
        """Generate location-based message for clock-out"""
        if not shift.clock_out_lat or not shift.clock_out_lng:
            return ""

        location_desc = get_location_description(shift.clock_out_lat, shift.clock_out_lng)
        
        if shift.is_outstation:
            return f"Clocked out at {location_desc}. Safe travels back to Batu Caves!"
        else:
            return f"Clocked out at {location_desc}. Thanks for your service today!"

    def _generate_shift_summary_message(self, shift: DriverShift) -> str:
        """Generate summary message with working hours and earnings"""
        hours = shift.total_working_hours or 0
        allowance = shift.outstation_allowance_amount or 0
        
        if hours > 0:
            hours_msg = f"Worked {hours:.1f} hours."
        else:
            hours_msg = "Shift completed."
            
        if allowance > 0:
            allowance_msg = f" Earned RM{allowance:.0f} outstation allowance."
        else:
            allowance_msg = ""
            
        return hours_msg + allowance_msg

    def get_logout_message_for_driver(self, driver_id: int) -> str:
        """Get logout message for a specific driver's last completed shift"""
        last_shift = self.db.query(DriverShift).filter(
            and_(
                DriverShift.driver_id == driver_id,
                DriverShift.status == "COMPLETED"
            )
        ).order_by(DriverShift.clock_out_at.desc()).first()

        if not last_shift:
            return "Thank you for your service today!"

        result = self.process_clock_out_logout(last_shift)
        return result.get("message", "Thank you for your service today!")

    def should_auto_logout_driver(self, driver_id: int) -> bool:
        """
        Check if driver should be auto-logged out
        
        Args:
            driver_id: Driver ID to check
            
        Returns:
            True if driver should be logged out, False otherwise
        """
        # Check if driver has any active shifts
        active_shift = self.db.query(DriverShift).filter(
            and_(
                DriverShift.driver_id == driver_id,
                DriverShift.status == "ACTIVE"
            )
        ).first()

        # Auto-logout if no active shift
        return active_shift is None