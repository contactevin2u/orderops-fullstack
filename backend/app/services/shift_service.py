"""Driver shift management service with 3AM KL auto-close"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.commission_entry import CommissionEntry
from app.repositories.shift_repo import ShiftRepo
from app.utils.geofencing import is_outstation_location, get_location_description
from app.config.clock_config import (
    OUTSTATION_ALLOWANCE_AMOUNT,
    MAX_SHIFT_DURATION_HOURS,
    AUTO_CLOCK_OUT_AFTER_HOURS
)

# Asia/Kuala_Lumpur timezone (UTC+8, no DST)
KL = timezone(timedelta(hours=8))
AUTO_CLOCKOUT_HOUR_LOCAL = 3  # 03:00 local time


class ShiftService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ShiftRepo(db)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _next_auto_cutoff_utc(self, start_utc: datetime) -> datetime:
        """
        Return the next occurrence of 03:00 KL that is on/after start_utc.
        If a shift starts 01:00 KL -> cutoff is the same day 03:00 KL.
        If it starts 10:00 KL -> cutoff is the next day 03:00 KL.
        """
        start_kl = start_utc.astimezone(KL)
        cutoff_date = start_kl.date()
        cutoff_kl = datetime(
            cutoff_date.year, cutoff_date.month, cutoff_date.day,
            AUTO_CLOCKOUT_HOUR_LOCAL, 0, 0, tzinfo=KL
        )
        if start_kl >= cutoff_kl:
            # already past today's 03:00 KL -> use tomorrow 03:00 KL
            cutoff_kl = cutoff_kl + timedelta(days=1)
        return cutoff_kl.astimezone(timezone.utc)

    def get_active_shift(self, driver_id: int) -> Optional[DriverShift]:
        """Get the active shift for a driver using safe projection"""
        return self.repo.get_active_shift_light(driver_id)

    def _close_shift(self, shift: DriverShift, closed_at: datetime, reason: str):
        """Close a shift using safe repository method"""
        self.repo.close_shift_at(shift.id, closed_at, reason)
        self.repo.calculate_working_hours(shift.id, closed_at)

    def clock_in(
        self,
        driver_id: int,
        location_lat: Optional[float] = None,
        location_lng: Optional[float] = None,
        location_name: Optional[str] = None,
        idempotent: bool = True,
    ) -> DriverShift:
        """
        Clock in a driver with idempotent 3AM KL auto-close logic
        
        Args:
            driver_id: Driver ID
            location_lat, location_lng: Clock-in coordinates
            location_name: Optional human-readable location name
            idempotent: If True, return active shift if within same service day
        
        Returns:
            DriverShift record (existing or new)
        
        Raises:
            ValueError: If driver not found/inactive, or non-idempotent with active shift
        """
        # Check if driver exists
        driver = self.db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise ValueError(f"Driver with ID {driver_id} not found")
        
        if not driver.is_active:
            raise ValueError(f"Driver {driver.name} is not active")

        now = self._now()
        active = self.get_active_shift(driver_id)

        if active:
            cutoff = self._next_auto_cutoff_utc(active.clock_in_at)
            if now >= cutoff:
                # Auto close at the policy boundary (exactly 03:00 KL)
                self._close_shift(active, cutoff, "AUTO_3AM")
                active = None
            else:
                # Within same service day → return active (idempotent)
                if idempotent:
                    return active
                raise ValueError(f"Active shift already open since {active.clock_in_at.isoformat()}")

        # Determine if location is outstation
        lat = location_lat or 3.1390  # Default to KL if not provided
        lng = location_lng or 101.6869
        is_outstation, distance_km = is_outstation_location(lat, lng)
        
        # Generate location description if not provided
        if not location_name:
            location_name = get_location_description(lat, lng)

        # Open a new shift using repository
        shift = self.repo.insert_shift(driver_id, now, lat, lng, location_name)
        
        # Update additional fields if needed
        if is_outstation:
            from sqlalchemy import update
            upd = (
                update(DriverShift)
                .where(DriverShift.id == shift.id)
                .values(
                    is_outstation=True,
                    outstation_distance_km=distance_km,
                    outstation_allowance_amount=OUTSTATION_ALLOWANCE_AMOUNT
                )
            )
            self.db.execute(upd)
            self.db.commit()

        # Create outstation allowance entry if applicable
        if is_outstation:
            self._create_outstation_allowance_entry(shift)

        return shift

    def clock_out(
        self, 
        driver_id: int, 
        lat: Optional[float] = None, 
        lng: Optional[float] = None, 
        location_name: Optional[str] = None,
        notes: Optional[str] = None,
        reason: str = "MANUAL"
    ) -> Optional[DriverShift]:
        """Clock out a driver - idempotent"""
        active = self.get_active_shift(driver_id)
        if not active:
            # idempotent: nothing to do
            return None
            
        now = self._now()
        
        # Update clock-out location details if provided
        if lat is not None:
            active.clock_out_lat = lat
        if lng is not None:
            active.clock_out_lng = lng
        if location_name:
            active.clock_out_location_name = location_name
        if notes:
            active.notes = notes
            
        self._close_shift(active, now, reason)
        return active

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

    def close_stale_shifts_3am(self) -> List[int]:
        """Admin sweep: close any forgotten shifts after 03:00 KL"""
        now = self._now()
        closed_ids = []
        
        # Use safe projection to get open shifts
        from sqlalchemy import select
        from sqlalchemy.orm import load_only
        
        stmt = (
            select(DriverShift)
            .options(load_only(DriverShift.id, DriverShift.clock_in_at))
            .where(DriverShift.clock_out_at.is_(None))
        )
        open_shifts = self.db.execute(stmt).scalars().all()
        
        for shift in open_shifts:
            cutoff = self._next_auto_cutoff_utc(shift.clock_in_at)
            if now >= cutoff:
                self.repo.close_shift_at(shift.id, cutoff, "AUTO_3AM_SWEEP")
                self.repo.calculate_working_hours(shift.id, cutoff)
                closed_ids.append(shift.id)

        return closed_ids

    def _create_outstation_allowance_entry(self, shift: DriverShift) -> CommissionEntry:
        """Create commission entry for outstation allowance"""
        entry = CommissionEntry(
            driver_id=shift.driver_id,
            shift_id=shift.id,
            entry_type="OUTSTATION_ALLOWANCE",
            amount=OUTSTATION_ALLOWANCE_AMOUNT,
            description=f"Outstation allowance - {shift.outstation_distance_km:.1f}km from Batu Caves (>100km)",
            status="EARNED",
            earned_at=shift.clock_in_at
        )
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        return entry