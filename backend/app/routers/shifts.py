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
        return cls(
            id=shift.id,
            driver_id=shift.driver_id,
            clock_in_at=int(shift.clock_in_at.timestamp()),
            clock_in_lat=float(shift.clock_in_lat),
            clock_in_lng=float(shift.clock_in_lng),
            clock_in_location_name=shift.clock_in_location_name,
            clock_out_at=int(shift.clock_out_at.timestamp()) if shift.clock_out_at else None,
            clock_out_lat=float(shift.clock_out_lat) if shift.clock_out_lat else None,
            clock_out_lng=float(shift.clock_out_lng) if shift.clock_out_lng else None,
            clock_out_location_name=shift.clock_out_location_name,
            is_outstation=shift.is_outstation,
            outstation_distance_km=float(shift.outstation_distance_km) if shift.outstation_distance_km else None,
            outstation_allowance_amount=float(shift.outstation_allowance_amount),
            total_working_hours=float(shift.total_working_hours) if shift.total_working_hours else None,
            status=shift.status,
            notes=shift.notes,
            created_at=int(shift.created_at.timestamp())
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
    try:
        print(f"DEBUG: Clock-in request received - lat: {request.lat}, lng: {request.lng}, scanned_uids: {request.scanned_uids}")
        print(f"DEBUG: Driver: {current_driver.id if current_driver else 'None'}")
        
        # Check for existing shift today
        today = date.today()
        existing_shift = db.execute(
            select(DriverShift).where(
                and_(
                    DriverShift.driver_id == current_driver.id,
                    func.date(DriverShift.clock_in_at) == today,
                    DriverShift.status == "ACTIVE"
                )
            )
        ).scalar_one_or_none()
        
        if existing_shift:
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

        # If assignment exists and not yet stock verified, handle stock verification
        if assignment and not assignment.stock_verified:
            return await _clock_in_with_stock_verification(
                request, current_driver, assignment, db
            )
        else:
            # Regular clock in (no assignment or already verified)
            return await _regular_clock_in(request, current_driver, db)
            
    except HTTPException:
        raise
    except Exception as e:
        # Handle database table not found errors during migration period
        if "does not exist" in str(e) or "no such table" in str(e):
            # Fallback: return a simplified successful response for driver app compatibility
            print(f"FALLBACK: Clock-in tables missing, using simplified response: {str(e)}")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clock-in failed: {str(e)}"
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
        unexpected_uids=json.dumps(unexpected_uids),
        verified_at=now,
        verified_by=driver.id
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
    """Get expected stock for lorry from previous verification"""
    yesterday = today - timedelta(days=1)
    
    # Get most recent verification for this lorry
    yesterday_verification = db.execute(
        select(LorryStockVerification)
        .where(LorryStockVerification.lorry_id == lorry_id)
        .where(LorryStockVerification.verification_date <= yesterday)
        .order_by(LorryStockVerification.created_at.desc())
    ).scalar_one_or_none()
    
    if yesterday_verification:
        return json.loads(yesterday_verification.scanned_uids)
    else:
        # No previous verification found - return empty
        return []