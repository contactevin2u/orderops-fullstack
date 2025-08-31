"""Tests for shift management service"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.commission_entry import CommissionEntry
from app.services.shift_service import ShiftService
from app.config.clock_config import HOME_BASE_LAT, HOME_BASE_LNG, OUTSTATION_ALLOWANCE_AMOUNT


class TestShiftService:
    def test_clock_in_success(self, db_session: Session):
        """Test successful clock-in"""
        # Create test driver
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # Clock in at home base
        shift = shift_service.clock_in(
            driver_id=driver.id,
            lat=HOME_BASE_LAT,
            lng=HOME_BASE_LNG,
            location_name="Batu Caves Office"
        )

        assert shift.driver_id == driver.id
        assert shift.status == "ACTIVE"
        assert shift.is_outstation is False
        assert shift.outstation_allowance_amount == 0
        assert shift.clock_in_location_name == "Batu Caves Office"

    def test_clock_in_outstation(self, db_session: Session):
        """Test clock-in at outstation location"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # Clock in at outstation (KL city center)
        shift = shift_service.clock_in(
            driver_id=driver.id,
            lat=3.1569,  # KL city center
            lng=101.7123,
            location_name="Kuala Lumpur City"
        )

        assert shift.is_outstation is True
        assert shift.outstation_allowance_amount == OUTSTATION_ALLOWANCE_AMOUNT
        assert shift.outstation_distance_km > 3.0

        # Check outstation allowance entry was created
        allowance_entry = db_session.query(CommissionEntry).filter(
            CommissionEntry.shift_id == shift.id,
            CommissionEntry.entry_type == "OUTSTATION_ALLOWANCE"
        ).first()
        
        assert allowance_entry is not None
        assert allowance_entry.amount == OUTSTATION_ALLOWANCE_AMOUNT

    def test_clock_in_already_active(self, db_session: Session):
        """Test clock-in fails when driver already has active shift"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # First clock-in
        shift_service.clock_in(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)
        
        # Second clock-in should fail
        with pytest.raises(ValueError, match="already has an active shift"):
            shift_service.clock_in(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)

    def test_clock_out_success(self, db_session: Session):
        """Test successful clock-out"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # Clock in
        shift = shift_service.clock_in(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)
        
        # Wait a moment (simulate working time)
        import time
        time.sleep(0.1)
        
        # Clock out
        completed_shift = shift_service.clock_out(
            driver_id=driver.id,
            lat=HOME_BASE_LAT + 0.001,
            lng=HOME_BASE_LNG + 0.001,
            notes="Test shift completed"
        )

        assert completed_shift.status == "COMPLETED"
        assert completed_shift.clock_out_at is not None
        assert completed_shift.total_working_hours is not None
        assert completed_shift.total_working_hours > 0
        assert completed_shift.notes == "Test shift completed"

    def test_clock_out_no_active_shift(self, db_session: Session):
        """Test clock-out fails when no active shift exists"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # Try to clock out without clocking in
        with pytest.raises(ValueError, match="No active shift found"):
            shift_service.clock_out(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)

    def test_get_active_shift(self, db_session: Session):
        """Test getting active shift for driver"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        shift_service = ShiftService(db_session)
        
        # No active shift initially
        assert shift_service.get_active_shift(driver.id) is None
        
        # Clock in
        shift = shift_service.clock_in(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)
        
        # Should find active shift
        active_shift = shift_service.get_active_shift(driver.id)
        assert active_shift is not None
        assert active_shift.id == shift.id
        
        # Clock out
        shift_service.clock_out(driver.id, HOME_BASE_LAT, HOME_BASE_LNG)
        
        # No active shift after clock-out
        assert shift_service.get_active_shift(driver.id) is None

    def test_shift_duration_calculation(self, db_session: Session):
        """Test working hours calculation"""
        driver = Driver(
            name="Test Driver",
            phone="+60123456789",
            firebase_uid="test-uid-123",
            is_active=True
        )
        db_session.add(driver)
        db_session.commit()

        # Create shift with specific times
        clock_in_time = datetime.now(timezone.utc)
        shift = DriverShift(
            driver_id=driver.id,
            clock_in_at=clock_in_time,
            clock_in_lat=HOME_BASE_LAT,
            clock_in_lng=HOME_BASE_LNG,
            clock_in_location_name="Test Location",
            status="ACTIVE"
        )
        db_session.add(shift)
        db_session.commit()

        # Clock out 8 hours later
        clock_out_time = clock_in_time + timedelta(hours=8)
        shift.clock_out_at = clock_out_time
        shift.status = "COMPLETED"
        
        # Calculate duration using property
        duration = shift.shift_duration_hours
        assert duration == 8.0