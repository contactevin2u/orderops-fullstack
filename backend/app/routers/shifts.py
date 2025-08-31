"""Driver shift management endpoints"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.auth.firebase import get_current_driver
from app.db import get_session
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
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_session)
):
    """Clock in driver at specified location"""
    try:
        shift_service = ShiftService(db)
        shift = shift_service.clock_in(
            driver_id=current_driver.id,
            lat=request.lat,
            lng=request.lng,
            location_name=request.location_name
        )
        return ShiftResponse.from_model(shift)
    except Exception as e:
        # Handle database table not found errors during migration period
        if "does not exist" in str(e) or "no such table" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clock-in system not yet available. Database migration in progress."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clock-in failed: {str(e)}"
        )


@router.post("/clock-out", response_model=ShiftResponse)
async def clock_out(
    request: ClockOutRequest,
    current_driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_session)
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
    current_driver: Driver = Depends(get_current_driver),
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
    current_driver: Driver = Depends(get_current_driver),
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
    current_driver: Driver = Depends(get_current_driver),
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
    current_driver: Driver = Depends(get_current_driver),
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