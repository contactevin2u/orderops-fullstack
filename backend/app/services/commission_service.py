"""Enhanced commission service with shift integration"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.trip import Trip
from app.models.commission import Commission
from app.models.commission_entry import CommissionEntry
from app.models.driver_shift import DriverShift
from app.models.order import Order


class CommissionService:
    def __init__(self, db: Session):
        self.db = db

    def create_delivery_commission_entry(
        self,
        trip: Trip,
        driver_id: int,
        commission_amount: float,
        driver_role: str,
        commission_scheme: str,
        order_value: float,
        commission_rate: float
    ) -> Optional[CommissionEntry]:
        """
        Create commission entry for a delivery when driver is clocked in
        
        Args:
            trip: Trip record
            driver_id: Driver ID earning the commission
            commission_amount: Amount to be earned
            driver_role: "primary" or "secondary"
            commission_scheme: Commission scheme name
            order_value: Total order value
            commission_rate: Commission rate used
        
        Returns:
            CommissionEntry if driver is clocked in, None otherwise
        """
        # Find active shift for this driver
        active_shift = self.db.query(DriverShift).filter(
            and_(
                DriverShift.driver_id == driver_id,
                DriverShift.status == "ACTIVE"
            )
        ).first()

        if not active_shift:
            # Driver not clocked in, no commission entry created
            return None

        # Create commission entry
        entry = CommissionEntry(
            driver_id=driver_id,
            shift_id=active_shift.id,
            order_id=trip.order_id,
            trip_id=trip.id,
            entry_type="DELIVERY",
            amount=commission_amount,
            description=f"Delivery commission - Order #{trip.order_id}",
            driver_role=driver_role,
            status="EARNED",
            base_commission_rate=commission_rate,
            order_value=order_value,
            commission_scheme=commission_scheme,
            earned_at=datetime.now(timezone.utc)
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    def get_shift_earnings(self, shift_id: int) -> dict:
        """Get total earnings breakdown for a shift"""
        shift = self.db.query(DriverShift).filter(DriverShift.id == shift_id).first()
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")

        commission_entries = self.db.query(CommissionEntry).filter(
            CommissionEntry.shift_id == shift_id
        ).all()

        delivery_commissions = [e for e in commission_entries if e.entry_type == "DELIVERY"]
        outstation_allowances = [e for e in commission_entries if e.entry_type == "OUTSTATION_ALLOWANCE"]

        total_delivery_commission = sum(e.amount for e in delivery_commissions)
        total_outstation_allowance = sum(e.amount for e in outstation_allowances)
        
        return {
            "shift_id": shift_id,
            "delivery_commission": total_delivery_commission,
            "outstation_allowance": total_outstation_allowance,
            "total_earnings": total_delivery_commission + total_outstation_allowance,
            "delivery_count": len(delivery_commissions),
            "working_hours": shift.total_working_hours,
            "commission_entries": commission_entries
        }

    def get_driver_monthly_earnings(self, driver_id: int, year: int, month: int) -> dict:
        """Get driver's total earnings for a specific month"""
        # Get all completed shifts for the month
        month_shifts = self.db.query(DriverShift).filter(
            and_(
                DriverShift.driver_id == driver_id,
                DriverShift.status == "COMPLETED",
                DriverShift.clock_in_at >= datetime(year, month, 1),
                DriverShift.clock_in_at < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
            )
        ).all()

        # Get all commission entries for these shifts
        shift_ids = [shift.id for shift in month_shifts]
        commission_entries = self.db.query(CommissionEntry).filter(
            CommissionEntry.shift_id.in_(shift_ids)
        ).all() if shift_ids else []

        # Calculate totals
        total_delivery_commission = sum(
            e.amount for e in commission_entries if e.entry_type == "DELIVERY"
        )
        total_outstation_allowance = sum(
            e.amount for e in commission_entries if e.entry_type == "OUTSTATION_ALLOWANCE"
        )
        total_working_hours = sum(
            shift.total_working_hours or 0 for shift in month_shifts
        )
        total_deliveries = len([
            e for e in commission_entries if e.entry_type == "DELIVERY"
        ])

        return {
            "driver_id": driver_id,
            "year": year,
            "month": month,
            "total_shifts": len(month_shifts),
            "total_working_hours": total_working_hours,
            "total_deliveries": total_deliveries,
            "delivery_commission": total_delivery_commission,
            "outstation_allowance": total_outstation_allowance,
            "total_earnings": total_delivery_commission + total_outstation_allowance,
            "shifts": month_shifts,
            "commission_entries": commission_entries
        }