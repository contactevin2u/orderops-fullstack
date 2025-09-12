"""Driver shift management endpoints"""

from datetime import datetime, timezone, date, timedelta
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, select, func

from app.auth.firebase import driver_auth
from app.db import get_session
from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.commission_entry import CommissionEntry
from app.models.lorry_assignment import LorryAssignment, LorryStockVerification, DriverHold
from app.services.shift_service import ShiftService
from app.utils.audit import log_action


router = APIRouter(prefix="/drivers/shifts", tags=["shifts"])


@router.get("/test")
async def test_shifts_available():
    """Test if shifts system is available"""
    return {"message": "Shifts API is available", "status": "ok"}


class ClockInRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable location name")
    scanned_uids: Optional[List[str]] = Field(None, description="UIDs scanned for stock verification (optional)")


class ClockOutRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable location name")
    notes: Optional[str] = Field(None, max_length=1000, description="Shift notes")


class ShiftResponse(BaseModel):
    id: int
    driver_id: int
    clock_in_at: int  # Unix timestamp
    clock_in_lat: float
    clock_in_lng: float
    clock_in_location_name: Optional[str]
    clock_out_at: Optional[int]  # Unix timestamp
    clock_out_lat: Optional[float]
    clock_out_lng: Optional[float]
    clock_out_location_name: Optional[str]
    is_outstation: bool
    outstation_distance_km: Optional[float]
    outstation_allowance_amount: float
    total_working_hours: Optional[float]
    status: str
    notes: Optional[str]
    created_at: int  # Unix timestamp

    @classmethod
    def from_model(cls, shift: "DriverShift") -> "ShiftResponse":
        """Create ShiftResponse from DriverShift model with graceful handling of missing columns"""
        return cls(
            id=shift.id,
            driver_id=shift.driver_id,
            clock_in_at=int(shift.clock_in_at.timestamp()),
            clock_in_lat=float(shift.clock_in_lat),
            clock_in_lng=float(shift.clock_in_lng),
            clock_in_location_name=getattr(shift, 'clock_in_location_name', None),
            clock_out_at=int(shift.clock_out_at.timestamp()) if getattr(shift, 'clock_out_at', None) else None,
            clock_out_lat=float(shift.clock_out_lat) if getattr(shift, 'clock_out_lat', None) else None,
            clock_out_lng=float(shift.clock_out_lng) if getattr(shift, 'clock_out_lng', None) else None,
            clock_out_location_name=getattr(shift, 'clock_out_location_name', None),
            is_outstation=getattr(shift, 'is_outstation', False),
            outstation_distance_km=float(shift.outstation_distance_km) if getattr(shift, 'outstation_distance_km', None) else None,
            outstation_allowance_amount=float(getattr(shift, 'outstation_allowance_amount', 0.0)),
            total_working_hours=float(shift.total_working_hours) if getattr(shift, 'total_working_hours', None) else None,
            status=getattr(shift, 'status', 'ACTIVE'),
            notes=getattr(shift, 'notes', None),
            created_at=int(getattr(shift, 'created_at', shift.clock_in_at).timestamp())
        )


class CommissionEntryResponse(BaseModel):
    id: int
    entry_type: str
    amount: float
    description: str
    driver_role: Optional[str]
    status: str
    earned_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class ShiftSummaryResponse(BaseModel):
    shift: ShiftResponse
    commission_entries: List[CommissionEntryResponse]
    total_commission: float
    delivery_count: int
    outstation_allowance: float
    total_earnings: float


@router.post("/clock-in", response_model=ShiftResponse)
async def clock_in(
    request: ClockInRequest,
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Unified clock in with automatic stock verification if lorry assignment exists"""
    print(f"DEBUG: Clock-in request received - lat: {request.lat}, lng: {request.lng}, scanned_uids: {request.scanned_uids}")
    print(f"DEBUG: Driver: {current_driver.id if current_driver else 'None'}")
    
    # Validate GPS coordinates - reject 0.0, 0.0 (no location)
    if request.lat == 0.0 and request.lng == 0.0:
        print("DEBUG: Invalid GPS coordinates (0.0, 0.0) - location services required")
        raise HTTPException(
            status_code=400, 
            detail="Valid GPS location is required for clock-in. Please enable location services."
        )
    
    try:
        
        # Check for existing shift today
        today = date.today()
        print(f"DEBUG: Checking for existing shift for driver {current_driver.id} on {today}")
        
        # Get all active shifts for this driver today to handle MultipleResultsFound error
        active_shifts_result = db.execute(
            select(DriverShift).where(
                and_(
                    DriverShift.driver_id == current_driver.id,
                    func.date(DriverShift.clock_in_at) == today,
                    DriverShift.status == "ACTIVE"
                )
            )
        ).fetchall()
        
        active_shifts = [row[0] for row in active_shifts_result]
        print(f"DEBUG: Found {len(active_shifts)} active shifts")
        
        # Clean up duplicate active shifts if any (defensive programming)
        if len(active_shifts) > 1:
            print(f"DEBUG: Cleaning up {len(active_shifts) - 1} duplicate active shifts")
            # Keep the most recent, mark others as completed
            active_shifts.sort(key=lambda s: s.clock_in_at, reverse=True)
            for duplicate_shift in active_shifts[1:]:
                duplicate_shift.status = "COMPLETED"
                duplicate_shift.clock_out_at = duplicate_shift.clock_in_at
                print(f"DEBUG: Marked duplicate shift {duplicate_shift.id} as completed")
            db.commit()
            active_shift = active_shifts[0] if active_shifts else None
        elif len(active_shifts) == 1:
            active_shift = active_shifts[0]
        else:
            active_shift = None
        
        print(f"DEBUG: Active shift after cleanup: {active_shift.id if active_shift else 'None'}")
        
        if active_shift:
            raise HTTPException(status_code=409, detail="Already clocked in today")

        # Check for lorry assignment
        assignment = db.execute(
            select(LorryAssignment).where(
                and_(
                    LorryAssignment.driver_id == current_driver.id,
                    LorryAssignment.assignment_date == today
                )
            )
        ).scalar_one_or_none()

        # Determine if this should be stock verification or regular clock-in
        has_scanned_uids = request.scanned_uids is not None and len(request.scanned_uids) >= 0
        print(f"DEBUG: Has scanned UIDs: {has_scanned_uids}, Assignment: {assignment is not None}, Stock verified: {assignment.stock_verified if assignment else 'N/A'}")
        
        # If assignment exists and not yet stock verified, and has scanned UIDs, do stock verification
        if assignment and not assignment.stock_verified and has_scanned_uids:
            print(f"DEBUG: Routing to stock verification clock-in")
            return await _clock_in_with_stock_verification(
                request, current_driver, assignment, db
            )
        else:
            # Regular clock in
            print(f"DEBUG: Routing to regular clock-in") 
            return await _regular_clock_in(request, current_driver, db)
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"DEBUG: Clock-in exception occurred: {error_msg}")
        print(f"DEBUG: Exception type: {type(e)}")
        
        # Handle database table not found errors during migration period
        if "does not exist" in error_msg or "no such table" in error_msg:
            # Fallback: return a simplified successful response for driver app compatibility
            print(f"FALLBACK: Clock-in tables missing, using simplified response: {error_msg}")
            return ShiftResponse(
                id=1,  # Placeholder
                driver_id=current_driver.id,
                clock_in_at=int(datetime.now(timezone.utc).timestamp()),
                clock_in_lat=request.lat,
                clock_in_lng=request.lng,
                clock_in_location_name=request.location_name,
                clock_out_at=None,
                clock_out_lat=None,
                clock_out_lng=None,
                clock_out_location_name=None,
                is_outstation=False,
                outstation_distance_km=None,
                outstation_allowance_amount=0.0,
                total_working_hours=None,
                status="ACTIVE",
                notes=f"Simplified clock-in. Scanned {len(request.scanned_uids or [])} items.",
                created_at=int(datetime.now(timezone.utc).timestamp())
            )
        else:
            print(f"ERROR: Non-table-missing error in clock-in: {error_msg}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clock-in failed: {error_msg}"
        )


@router.post("/clock-out", response_model=ShiftResponse)
async def clock_out(
    request: ClockOutRequest,
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Clock out driver at specified location"""
    try:
        shift_service = ShiftService(db)
        shift = shift_service.clock_out(
            driver_id=current_driver.id,
            lat=request.lat,
            lng=request.lng,
            location_name=request.location_name,
            notes=request.notes
        )
        return ShiftResponse.from_model(shift)
    except Exception as e:
        # Handle database table not found errors during migration period
        if "does not exist" in str(e) or "no such table" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clock-out system not yet available. Database migration in progress."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clock-out failed: {str(e)}"
        )


@router.get("/active", response_model=Optional[ShiftResponse])
async def get_active_shift(
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get current active shift for driver"""
    shift_service = ShiftService(db)
    shift = shift_service.get_active_shift(current_driver.id)
    return ShiftResponse.from_model(shift) if shift else None


@router.get("/history", response_model=List[ShiftResponse])
async def get_shift_history(
    limit: int = 10,
    include_active: bool = True,
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver's shift history"""
    shift_service = ShiftService(db)
    shifts = shift_service.get_driver_shifts(
        driver_id=current_driver.id,
        limit=limit,
        include_active=include_active
    )
    return [ShiftResponse.from_model(shift) for shift in shifts]


@router.get("/{shift_id}/summary", response_model=ShiftSummaryResponse)
async def get_shift_summary(
    shift_id: int,
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get detailed shift summary including commission breakdown"""
    shift_service = ShiftService(db)
    
    # Verify shift belongs to current driver
    shift = db.query(DriverShift).filter(
        and_(
            DriverShift.id == shift_id,
            DriverShift.driver_id == current_driver.id
        )
    ).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    try:
        summary = shift_service.get_shift_summary(shift_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/status")
async def get_shift_status(
    current_driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver's current shift status and basic info"""
    try:
        shift_service = ShiftService(db)
        active_shift = shift_service.get_active_shift(current_driver.id)
        
        if not active_shift:
            return {
                "is_clocked_in": False,
                "message": "Ready to clock in"
            }
        
        hours_worked = (datetime.now(timezone.utc) - active_shift.clock_in_at).total_seconds() / 3600
        
        return {
            "is_clocked_in": True,
            "shift_id": active_shift.id,
            "clock_in_at": int(active_shift.clock_in_at.timestamp()),
            "hours_worked": round(hours_worked, 2),
            "is_outstation": active_shift.is_outstation,
            "location": active_shift.clock_in_location_name,
            "message": f"Clocked in since {active_shift.clock_in_at.strftime('%H:%M')}"
        }
    except Exception as e:
        # Handle database table not found errors during migration period
        if "does not exist" in str(e) or "no such table" in str(e):
            return {
                "is_clocked_in": False,
                "message": "Clock-in system not yet available"
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shift status: {str(e)}"
        )


# Helper functions for unified clock-in

async def _regular_clock_in(
    request: ClockInRequest, 
    driver: Driver, 
    db: Session
) -> ShiftResponse:
    """Regular clock in without stock verification"""
    shift_service = ShiftService(db)
    shift = shift_service.clock_in(
        driver_id=driver.id,
        lat=request.lat,
        lng=request.lng,
        location_name=request.location_name
    )
    return ShiftResponse.from_model(shift)


async def _clock_in_with_stock_verification(
    request: ClockInRequest,
    driver: Driver, 
    assignment: LorryAssignment,
    db: Session
) -> ShiftResponse:
    """Clock in with lorry stock verification"""
    scanned_uids = request.scanned_uids or []
    today = date.today()
    
    # Create shift record first
    now = datetime.now()
    shift = DriverShift(
        driver_id=driver.id,
        clock_in_at=now,
        clock_in_lat=request.lat,
        clock_in_lng=request.lng,
        clock_in_location_name=request.location_name,
        is_outstation=False,  # Can be enhanced later
        status="ACTIVE"
    )
    
    db.add(shift)
    db.flush()  # Get shift ID
    
    # Update assignment with shift
    assignment.shift_id = shift.id
    assignment.status = "ACTIVE"
    
    # Process stock verification
    variance_detected = False
    missing_uids = []
    unexpected_uids = []
    
    # Get expected UIDs for this lorry from previous day's verification
    expected_uids = await _get_expected_lorry_stock(db, assignment.lorry_id, today)
    
    # Detect variances
    scanned_set = set(scanned_uids)
    expected_set = set(expected_uids)
    
    missing_uids = list(expected_set - scanned_set)  # Expected but not scanned
    unexpected_uids = list(scanned_set - expected_set)  # Scanned but not expected
    
    variance_detected = len(missing_uids) > 0 or len(unexpected_uids) > 0
    variance_count = len(missing_uids) + len(unexpected_uids)
    
    # Create stock verification record
    verification = LorryStockVerification(
        assignment_id=assignment.id,
        driver_id=driver.id,
        lorry_id=assignment.lorry_id,
        verification_date=today,
        scanned_uids=json.dumps(scanned_uids),
        total_scanned=len(scanned_uids),
        expected_uids=json.dumps(expected_uids),
        total_expected=len(expected_uids),
        variance_count=variance_count,
        missing_uids=json.dumps(missing_uids),
        unexpected_uids=json.dumps(unexpected_uids)
    )
    
    db.add(verification)
    db.flush()  # Get verification ID
    
    # Mark assignment as stock verified
    assignment.stock_verified = True
    assignment.stock_verified_at = now
    
    # Create driver hold if variance detected
    if variance_detected:
        hold_description = f"Stock variance detected for lorry {assignment.lorry_id}:"
        if missing_uids:
            hold_description += f" Missing {len(missing_uids)} items"
        if unexpected_uids:
            hold_description += f" Unexpected {len(unexpected_uids)} items"
            
        hold = DriverHold(
            driver_id=driver.id,
            reason="STOCK_VARIANCE",
            description=hold_description,
            status="ACTIVE",
            created_by=1,  # System-generated
            related_assignment_id=assignment.id,
            related_verification_id=verification.id
        )
        db.add(hold)
    
    # Commit all changes
    db.commit()
    
    # Log audit trail
    log_action(
        db=db, 
        user_id=driver.id, 
        action="UNIFIED_CLOCK_IN_WITH_STOCK", 
        resource_type="driver_shift", 
        resource_id=shift.id,
        details={
            "lorry_id": assignment.lorry_id,
            "scanned_uids_count": len(scanned_uids),
            "variance_detected": variance_detected,
            "variance_count": variance_count
        }
    )
    
    return ShiftResponse.from_model(shift)


async def _get_expected_lorry_stock(db: Session, lorry_id: str, today: date) -> list:
    """Get expected stock for lorry from actual transaction records"""
    from app.services.lorry_inventory_service import LorryInventoryService
    
    # Use the unified lorry inventory service to get actual current stock
    inventory_service = LorryInventoryService(db)
    
    # Get stock as of end of previous day (what should be in lorry for morning verification)
    yesterday = today - timedelta(days=1)
    expected_uids = inventory_service.get_current_stock(lorry_id, yesterday)
    
    return expected_uids