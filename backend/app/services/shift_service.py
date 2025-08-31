"""Driver shift management service"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.commission_entry import CommissionEntry
from app.utils.geofencing import is_outstation_location, get_location_description
from app.config.clock_config import (
    OUTSTATION_ALLOWANCE_AMOUNT,
    MAX_SHIFT_DURATION_HOURS,
    AUTO_CLOCK_OUT_AFTER_HOURS
)


class ShiftService:
    def __init__(self, db: Session):
        self.db = db

    def clock_in(
        self, 
        driver_id: int, 
        lat: float, 
        lng: float, 
        location_name: Optional[str] = None
    ) -> DriverShift:
        """
        Clock in a driver at the specified location
        
        Args:
            driver_id: Driver ID
            lat, lng: Clock-in coordinates
            location_name: Optional human-readable location name
        
        Returns:
            Created DriverShift record
        
        Raises:
            ValueError: If driver already has active shift or other validation errors
        """
        # Check if driver exists
        driver = self.db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise ValueError(f"Driver with ID {driver_id} not found")
        
        if not driver.is_active:
            raise ValueError(f"Driver {driver.name} is not active")

        # Check if driver already has an active shift
        active_shift = self.get_active_shift(driver_id)
        if active_shift:
            raise ValueError(f"Driver already has an active shift started at {active_shift.clock_in_at}")

        # Determine if location is outstation
        is_outstation, distance_km = is_outstation_location(lat, lng)
        
        # Generate location description if not provided
        if not location_name:
            location_name = get_location_description(lat, lng)

        # Create new shift
        shift = DriverShift(
            driver_id=driver_id,
            clock_in_at=datetime.now(timezone.utc),
            clock_in_lat=lat,
            clock_in_lng=lng,
            clock_in_location_name=location_name,
            is_outstation=is_outstation,
            outstation_distance_km=distance_km if is_outstation else None,
            outstation_allowance_amount=OUTSTATION_ALLOWANCE_AMOUNT if is_outstation else 0,
            status="ACTIVE"
        )
        
        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)

        # Create outstation allowance entry if applicable
        if is_outstation:
            self._create_outstation_allowance_entry(shift)

        return shift

    def clock_out(
        self, 
        driver_id: int, 
        lat: float, 
        lng: float, 
        location_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> DriverShift:
        """
        Clock out a driver at the specified location
        
        Args:
            driver_id: Driver ID
            lat, lng: Clock-out coordinates
            location_name: Optional human-readable location name
            notes: Optional shift notes
        
        Returns:
            Updated DriverShift record
        
        Raises:
            ValueError: If no active shift found or other validation errors
        """
        # Get active shift
        active_shift = self.get_active_shift(driver_id)
        if not active_shift:
            raise ValueError(f"No active shift found for driver {driver_id}")

        # Generate location description if not provided
        if not location_name:
            location_name = get_location_description(lat, lng)

        # Update shift with clock-out details
        clock_out_time = datetime.now(timezone.utc)
        total_hours = (clock_out_time - active_shift.clock_in_at).total_seconds() / 3600

        # Validate shift duration
        if total_hours > MAX_SHIFT_DURATION_HOURS:
            raise ValueError(f"Shift duration ({total_hours:.1f}h) exceeds maximum allowed ({MAX_SHIFT_DURATION_HOURS}h)")

        active_shift.clock_out_at = clock_out_time
        active_shift.clock_out_lat = lat
        active_shift.clock_out_lng = lng
        active_shift.clock_out_location_name = location_name
        active_shift.total_working_hours = total_hours
        active_shift.status = "COMPLETED"
        active_shift.notes = notes

        self.db.commit()
        self.db.refresh(active_shift)

        return active_shift

    def get_active_shift(self, driver_id: int) -> Optional[DriverShift]:
        """Get the active shift for a driver"""
        return self.db.query(DriverShift).filter(
            and_(
                DriverShift.driver_id == driver_id,
                DriverShift.status == "ACTIVE"
            )
        ).first()

    def get_driver_shifts(
        self, 
        driver_id: int, 
        limit: int = 10, 
        include_active: bool = True
    ) -> List[DriverShift]:
        """Get recent shifts for a driver"""
        query = self.db.query(DriverShift).filter(DriverShift.driver_id == driver_id)
        
        if not include_active:
            query = query.filter(DriverShift.status == "COMPLETED")
        
        return query.order_by(desc(DriverShift.clock_in_at)).limit(limit).all()

    def get_shift_summary(self, shift_id: int) -> Dict[str, Any]:
        """Get comprehensive shift summary including commission entries"""
        shift = self.db.query(DriverShift).filter(DriverShift.id == shift_id).first()
        if not shift:
            raise ValueError(f"Shift with ID {shift_id} not found")

        commission_entries = self.db.query(CommissionEntry).filter(
            CommissionEntry.shift_id == shift_id
        ).all()

        total_commission = sum(entry.amount for entry in commission_entries)
        delivery_count = len([e for e in commission_entries if e.entry_type == "DELIVERY"])

        return {
            "shift": shift,
            "commission_entries": commission_entries,
            "total_commission": total_commission,
            "delivery_count": delivery_count,
            "outstation_allowance": shift.outstation_allowance_amount,
            "total_earnings": total_commission + shift.outstation_allowance_amount
        }

    def auto_clock_out_expired_shifts(self) -> List[DriverShift]:
        """Auto clock-out shifts that have exceeded maximum duration"""
        cutoff_time = datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour - int(AUTO_CLOCK_OUT_AFTER_HOURS)
        )
        
        expired_shifts = self.db.query(DriverShift).filter(
            and_(
                DriverShift.status == "ACTIVE",
                DriverShift.clock_in_at < cutoff_time
            )
        ).all()

        for shift in expired_shifts:
            # Auto clock-out at last known location or home base
            shift.clock_out_at = datetime.now(timezone.utc)
            shift.clock_out_lat = shift.clock_in_lat
            shift.clock_out_lng = shift.clock_in_lng
            shift.clock_out_location_name = f"Auto clock-out: {shift.clock_in_location_name}"
            shift.total_working_hours = AUTO_CLOCK_OUT_AFTER_HOURS
            shift.status = "COMPLETED"
            shift.notes = f"Auto-clocked out after {AUTO_CLOCK_OUT_AFTER_HOURS} hours"

        if expired_shifts:
            self.db.commit()

        return expired_shifts

    def _create_outstation_allowance_entry(self, shift: DriverShift) -> CommissionEntry:
        """Create commission entry for outstation allowance"""
        entry = CommissionEntry(
            driver_id=shift.driver_id,
            shift_id=shift.id,
            entry_type="OUTSTATION_ALLOWANCE",
            amount=OUTSTATION_ALLOWANCE_AMOUNT,
            description=f"Outstation allowance - {shift.outstation_distance_km:.1f}km from Batu Caves",
            status="EARNED",
            earned_at=shift.clock_in_at
        )
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        return entry