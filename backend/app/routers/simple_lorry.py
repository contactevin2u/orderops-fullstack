from datetime import datetime, date
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_
from sqlalchemy.exc import IntegrityError
import json
from fastapi.exceptions import RequestValidationError

from ..db import get_session
from ..models import Lorry, Driver
from ..auth.deps import require_roles, Role, get_current_user
from ..utils.responses import envelope


router = APIRouter(
    prefix="/lorry-management",
    tags=["lorry-management"],
)

logger = logging.getLogger(__name__)


# Pydantic models for basic lorry operations
class CreateLorryRequest(BaseModel):
    lorry_id: str
    plate_number: Optional[str] = None
    model: Optional[str] = None
    capacity: Optional[str] = None
    base_warehouse: str = "BATU_CAVES"
    notes: Optional[str] = None
    
    @validator('lorry_id')
    def validate_lorry_id(cls, v):
        if not v or not v.strip():
            raise ValueError('lorry_id cannot be empty')
        if len(v) > 50:
            raise ValueError('lorry_id cannot exceed 50 characters')
        return v.strip()
    
    @validator('base_warehouse')
    def validate_base_warehouse(cls, v):
        if len(v) > 20:
            raise ValueError('base_warehouse cannot exceed 20 characters')
        return v


class UpdatePriorityLorryRequest(BaseModel):
    priority_lorry_id: Optional[str] = None


class LorryResponse(BaseModel):
    id: int
    lorry_id: str
    plate_number: Optional[str]
    model: Optional[str]
    capacity: Optional[str]
    base_warehouse: str
    is_active: bool
    is_available: bool
    notes: Optional[str]
    created_at: str


async def parse_lorry_request(request: Request) -> CreateLorryRequest:
    """Parse lorry request from either JSON object or JSON string"""
    try:
        # First try to get as normal JSON
        body = await request.json()
        return CreateLorryRequest(**body)
    except Exception as e:
        # If that fails, try to get as text and parse as JSON string
        try:
            body_text = await request.body()
            body_str = body_text.decode('utf-8')
            
            # If it's already a JSON string, parse it
            if body_str.startswith('"') and body_str.endswith('"'):
                # Remove outer quotes and unescape
                body_str = json.loads(body_str)
            
            # Parse the JSON string
            body_dict = json.loads(body_str)
            return CreateLorryRequest(**body_dict)
        except Exception as parse_error:
            logger.error(f"Failed to parse request body: {parse_error}")
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid request format. Expected JSON object or valid JSON string. Error: {str(parse_error)}"
            )


@router.post("/lorries", response_model=Dict[str, Any])
async def create_lorry(
    raw_request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Create a new lorry"""
    try:
        # Parse the request using our robust parser
        request = await parse_lorry_request(raw_request)
        
        logger.info(f"Creating lorry request: {request.dict()}")
        logger.info(f"Current user: {getattr(current_user, 'username', getattr(current_user, 'email', 'unknown'))}")
        # Check if lorry_id already exists
        existing = db.execute(
            select(Lorry).where(Lorry.lorry_id == request.lorry_id)
        ).scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Lorry with ID {request.lorry_id} already exists"
            )
        
        # Create new lorry
        lorry = Lorry(
            lorry_id=request.lorry_id,
            plate_number=request.plate_number,
            model=request.model,
            capacity=request.capacity,
            base_warehouse=request.base_warehouse,
            notes=request.notes,
            is_active=True,
            is_available=True
        )
        
        db.add(lorry)
        db.commit()
        db.refresh(lorry)
        
        logger.info(f"Created new lorry: {request.lorry_id}")
        
        return envelope({
            "success": True,
            "message": f"Successfully created lorry {request.lorry_id}",
            "lorry": {
                "id": lorry.id,
                "lorry_id": lorry.lorry_id,
                "plate_number": lorry.plate_number,
                "model": lorry.model,
                "capacity": lorry.capacity,
                "base_warehouse": lorry.base_warehouse,
                "is_active": lorry.is_active,
                "is_available": lorry.is_available,
                "notes": lorry.notes,
                "created_at": lorry.created_at.isoformat()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating lorry {request.lorry_id}: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating lorry: {str(e)}"
        )


@router.get("/lorries", response_model=Dict[str, Any])
async def get_all_lorries(
    include_inactive: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get all lorries"""
    try:
        query = select(Lorry)
        
        if not include_inactive:
            query = query.where(Lorry.is_active == True)
        
        lorries = db.execute(query.order_by(Lorry.lorry_id)).scalars().all()
        
        return envelope({
            "lorries": [
                {
                    "id": lorry.id,
                    "lorry_id": lorry.lorry_id,
                    "plate_number": lorry.plate_number,
                    "model": lorry.model,
                    "capacity": lorry.capacity,
                    "base_warehouse": lorry.base_warehouse,
                    "is_active": lorry.is_active,
                    "is_available": lorry.is_available,
                    "notes": lorry.notes,
                    "current_location": lorry.current_location,
                    "last_maintenance_date": lorry.last_maintenance_date.isoformat() if lorry.last_maintenance_date else None,
                    "created_at": lorry.created_at.isoformat(),
                    "updated_at": lorry.updated_at.isoformat()
                }
                for lorry in lorries
            ]
        })
        
    except Exception as e:
        logger.error(f"Error fetching lorries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching lorries: {str(e)}"
        )


@router.post("/test-validation")
async def test_validation(
    request: CreateLorryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Test endpoint to debug validation issues"""
    return envelope({
        "message": "Validation successful",
        "request_data": request.dict(),
        "user": getattr(current_user, 'username', getattr(current_user, 'email', 'unknown'))
    })


@router.get("/status")
async def get_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get basic status for lorry management"""
    try:
        total_lorries = db.execute(
            select(func.count(Lorry.id)).where(Lorry.is_active == True)
        ).scalar()
        
        available_lorries = db.execute(
            select(func.count(Lorry.id)).where(
                and_(Lorry.is_active == True, Lorry.is_available == True)
            )
        ).scalar()
        
        return envelope({
            "total_lorries": total_lorries or 0,
            "available_lorries": available_lorries or 0,
            "assigned_lorries": (total_lorries or 0) - (available_lorries or 0)
        })
        
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching status: {str(e)}"
        )


@router.get("/drivers", response_model=Dict[str, Any])
async def get_drivers_with_priority_lorries(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get all active drivers with their priority lorry assignments"""
    try:
        drivers = db.execute(
            select(Driver).where(Driver.is_active == True).order_by(Driver.name)
        ).scalars().all()
        
        return envelope({
            "drivers": [
                {
                    "id": driver.id,
                    "name": driver.name,
                    "phone": driver.phone,
                    "firebase_uid": driver.firebase_uid,
                    "base_warehouse": driver.base_warehouse,
                    "priority_lorry_id": driver.priority_lorry_id,
                    "is_active": driver.is_active,
                    "created_at": driver.created_at.isoformat() if driver.created_at else None
                }
                for driver in drivers
            ]
        })
        
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching drivers: {str(e)}"
        )


@router.patch("/drivers/{driver_id}/priority-lorry", response_model=Dict[str, Any])
async def update_driver_priority_lorry(
    driver_id: int,
    request: UpdatePriorityLorryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Update driver's priority lorry assignment"""
    try:
        # Get the driver
        driver = db.execute(
            select(Driver).where(Driver.id == driver_id)
        ).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
        
        # Extract priority_lorry_id from request
        priority_lorry_id = request.priority_lorry_id
        
        # Validate lorry exists if provided
        if priority_lorry_id:
            existing_lorry = db.execute(
                select(Lorry).where(Lorry.lorry_id == priority_lorry_id)
            ).scalar_one_or_none()
            
            if not existing_lorry:
                raise HTTPException(status_code=400, detail=f"Lorry {priority_lorry_id} not found")
        
        # Update driver's priority lorry
        driver.priority_lorry_id = priority_lorry_id
        db.commit()
        db.refresh(driver)
        
        logger.info(f"Updated driver {driver_id} priority lorry to: {priority_lorry_id}")
        
        return envelope({
            "success": True,
            "message": f"Updated priority lorry for {driver.name or f'Driver {driver_id}'}",
            "driver": {
                "id": driver.id,
                "name": driver.name,
                "priority_lorry_id": driver.priority_lorry_id
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating driver priority lorry: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating priority lorry: {str(e)}"
        )


@router.get("/assignments", response_model=Dict[str, Any])
async def get_lorry_assignments(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get lorry assignments - placeholder endpoint"""
    return envelope([])


@router.get("/holds", response_model=Dict[str, Any]) 
async def get_driver_holds(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get driver holds - placeholder endpoint"""
    return envelope([])


@router.get("/stock/summary", response_model=Dict[str, Any])
async def get_stock_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get lorry stock summary - placeholder endpoint"""
    return envelope({"lorries": []})


@router.get("/stock/transactions", response_model=Dict[str, Any])
async def get_stock_transactions(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get stock transactions - placeholder endpoint"""
    return envelope([])


@router.get("/assignment-status", response_model=Dict[str, Any])
async def get_assignment_status(
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get assignment status - placeholder endpoint"""
    return envelope({
        "assignment_date": date or "2025-09-08",
        "scheduled_drivers": 0,
        "assigned_drivers": 0, 
        "unassigned_drivers": 0,
        "available_lorries": 0,
        "can_auto_assign": False,
        "assignments": []
    })