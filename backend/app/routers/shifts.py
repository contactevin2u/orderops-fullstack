"""Driver shift management endpoints"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.firebase import get_current_driver
from app.database import get_db
from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.commission_entry import CommissionEntry
from app.services.shift_service import ShiftService


router = APIRouter(prefix="/drivers/shifts", tags=["shifts"])


class ClockInRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable location name")


class ClockOutRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable location name")
    notes: Optional[str] = Field(None, max_length=1000, description="Shift notes")


class ShiftResponse(BaseModel):
    id: int
    driver_id: int
    clock_in_at: datetime
    clock_in_lat: float
    clock_in_lng: float
    clock_in_location_name: Optional[str]
    clock_out_at: Optional[datetime]
    clock_out_lat: Optional[float]
    clock_out_lng: Optional[float]
    clock_out_location_name: Optional[str]
    is_outstation: bool
    outstation_distance_km: Optional[float]
    outstation_allowance_amount: float
    total_working_hours: Optional[float]
    status: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


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
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Clock in driver at specified location"""
    shift_service = ShiftService(db)
    
    try:
        shift = shift_service.clock_in(
            driver_id=current_driver.id,
            lat=request.lat,
            lng=request.lng,
            location_name=request.location_name
        )
        return shift
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/clock-out", response_model=ShiftResponse)
async def clock_out(
    request: ClockOutRequest,
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Clock out driver at specified location"""
    shift_service = ShiftService(db)
    
    try:
        shift = shift_service.clock_out(
            driver_id=current_driver.id,
            lat=request.lat,
            lng=request.lng,
            location_name=request.location_name,
            notes=request.notes
        )
        return shift
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/active", response_model=Optional[ShiftResponse])
async def get_active_shift(
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get current active shift for driver"""
    shift_service = ShiftService(db)
    shift = shift_service.get_active_shift(current_driver.id)
    return shift


@router.get("/history", response_model=List[ShiftResponse])
async def get_shift_history(
    limit: int = 10,
    include_active: bool = True,
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver's shift history"""
    shift_service = ShiftService(db)
    shifts = shift_service.get_driver_shifts(
        driver_id=current_driver.id,
        limit=limit,
        include_active=include_active
    )
    return shifts


@router.get("/{shift_id}/summary", response_model=ShiftSummaryResponse)
async def get_shift_summary(
    shift_id: int,
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
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
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver's current shift status and basic info"""
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
        "clock_in_at": active_shift.clock_in_at,
        "hours_worked": round(hours_worked, 2),
        "is_outstation": active_shift.is_outstation,
        "location": active_shift.clock_in_location_name,
        "message": f"Clocked in since {active_shift.clock_in_at.strftime('%H:%M')}"
    }