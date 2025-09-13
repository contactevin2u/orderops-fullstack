from datetime import date
from sqlalchemy import select, func, update, insert
from sqlalchemy.sql import func as sa_func
from sqlalchemy.orm import Session, load_only
from app.models.driver_shift import DriverShift


class ShiftRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_active_shift_light(self, driver_id: int):
        """Get active shift with only essential columns - safe even if closure_reason column missing"""
        stmt = (
            select(DriverShift)
            .options(
                load_only(
                    DriverShift.id,
                    DriverShift.driver_id,
                    DriverShift.clock_in_at,
                    DriverShift.clock_out_at,
                    DriverShift.status,
                    DriverShift.clock_in_lat,
                    DriverShift.clock_in_lng,
                    DriverShift.clock_in_location_name,
                    DriverShift.is_outstation,
                    DriverShift.outstation_allowance_amount,
                    DriverShift.created_at,
                )
            )
            .where(DriverShift.driver_id == driver_id, DriverShift.clock_out_at.is_(None))
            .order_by(DriverShift.clock_in_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_shift_for_day_light(self, driver_id: int, d: date):
        """Get shift for specific day with only essential columns"""
        stmt = (
            select(DriverShift)
            .options(
                load_only(
                    DriverShift.id,
                    DriverShift.driver_id,
                    DriverShift.clock_in_at,
                    DriverShift.clock_out_at,
                    DriverShift.status,
                    DriverShift.clock_in_lat,
                    DriverShift.clock_in_lng,
                    DriverShift.clock_in_location_name,
                    DriverShift.is_outstation,
                    DriverShift.outstation_allowance_amount,
                    DriverShift.created_at,
                )
            )
            .where(
                DriverShift.driver_id == driver_id,
                func.date(DriverShift.clock_in_at) == d,
            )
            .order_by(DriverShift.clock_in_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def close_shift_at(self, shift_id: int, closed_at, reason: str | None = None):
        """Close shift with targeted UPDATE - won't fail if closure_reason column missing"""
        # Always set clock_out_at
        upd = (
            update(DriverShift)
            .where(DriverShift.id == shift_id)
            .values(clock_out_at=closed_at, status="COMPLETED")
        )
        self.db.execute(upd)
        
        # Best-effort: set reason if column exists (do not fail if missing)
        if reason:
            try:
                upd2 = (
                    update(DriverShift)
                    .where(DriverShift.id == shift_id)
                    .values(closure_reason=reason)
                )
                self.db.execute(upd2)
            except Exception:
                # Column not present - ignore silently
                pass
        
        self.db.commit()

    def insert_shift(self, driver_id: int, now, loc_lat, loc_lng, loc_name):
        """Insert new shift record via Core INSERT (exclude closure_reason; return all required fields)."""
        tbl = DriverShift.__table__
        stmt = (
            insert(tbl)
            .values(
                driver_id=driver_id,
                clock_in_at=now,
                clock_in_lat=loc_lat,
                clock_in_lng=loc_lng,
                clock_in_location_name=loc_name,
                clock_out_at=None,
                is_outstation=False,
                outstation_distance_km=None,
                outstation_allowance_amount=0,
                total_working_hours=None,
                status="ACTIVE",
                notes=None,
                # ensure created_at if model doesn't default it
                created_at=sa_func.now(),
                updated_at=sa_func.now(),
                # NOTE: closure_reason intentionally NOT set here
            )
            .returning(
                tbl.c.id,
                tbl.c.driver_id,
                tbl.c.clock_in_at,
                tbl.c.clock_in_lat,
                tbl.c.clock_in_lng,
                tbl.c.clock_in_location_name,
                tbl.c.clock_out_at,
                tbl.c.is_outstation,
                tbl.c.outstation_allowance_amount,
                tbl.c.status,
                tbl.c.created_at,
                tbl.c.updated_at,
            )
        )
        row = self.db.execute(stmt).first()
        self.db.commit()

        # Return a lightweight object with the fields callers actually use
        class _ShiftLite:
            __slots__ = (
                "id", "driver_id", "clock_in_at", "clock_in_lat", "clock_in_lng",
                "clock_in_location_name", "clock_out_at", "is_outstation",
                "outstation_allowance_amount", "status", "created_at", "updated_at",
            )
        s = _ShiftLite()
        s.id = row.id
        s.driver_id = row.driver_id
        s.clock_in_at = row.clock_in_at
        s.clock_in_lat = row.clock_in_lat
        s.clock_in_lng = row.clock_in_lng
        s.clock_in_location_name = row.clock_in_location_name
        s.clock_out_at = row.clock_out_at
        s.is_outstation = row.is_outstation
        s.outstation_allowance_amount = row.outstation_allowance_amount
        s.status = row.status
        s.created_at = row.created_at
        s.updated_at = row.updated_at
        return s

    def calculate_working_hours(self, shift_id: int, clock_out_at):
        """Calculate and update working hours for completed shift"""
        try:
            # Get shift to calculate hours
            shift = self.db.execute(
                select(DriverShift)
                .options(load_only(DriverShift.clock_in_at))
                .where(DriverShift.id == shift_id)
            ).scalars().first()
            
            if shift:
                total_hours = (clock_out_at - shift.clock_in_at).total_seconds() / 3600
                upd = (
                    update(DriverShift)
                    .where(DriverShift.id == shift_id)
                    .values(total_working_hours=total_hours)
                )
                self.db.execute(upd)
                self.db.commit()
        except Exception:
            # Best effort - don't fail the clock-out if this fails
            pass