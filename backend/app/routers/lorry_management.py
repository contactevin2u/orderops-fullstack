from datetime import datetime, date, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_
from sqlalchemy.exc import IntegrityError
import json

from ..db import get_session
from ..models import (
    LorryAssignment, 
    LorryStockVerification, 
    DriverHold, 
    Driver, 
    DriverShift, 
    Item,
    User
)
from ..auth.deps import require_roles, Role, get_current_user
from ..auth.firebase import driver_auth
from ..core.config import settings
from ..utils.responses import envelope
from ..utils.audit import log_action


router = APIRouter(
    prefix="/lorry-management",
    tags=["lorry-management"],
)

# Pydantic models for request/response
class LorryAssignmentRequest(BaseModel):
    driver_id: int
    lorry_id: str
    assignment_date: str  # YYYY-MM-DD
    notes: Optional[str] = None

class LorryAssignmentResponse(BaseModel):
    id: int
    driver_id: int
    driver_name: str
    lorry_id: str
    assignment_date: str
    status: str
    stock_verified: bool
    stock_verified_at: Optional[str] = None
    shift_id: Optional[int] = None
    assigned_by: int
    assigned_at: str
    notes: Optional[str] = None

class StockVerificationRequest(BaseModel):
    scanned_uids: List[str]
    notes: Optional[str] = None

class StockVerificationResponse(BaseModel):
    success: bool
    total_scanned: int
    total_expected: int
    variance_count: int
    missing_uids: List[str]
    unexpected_uids: List[str]
    message: str

class DriverHoldRequest(BaseModel):
    driver_id: int
    reason: str
    description: str
    related_assignment_id: Optional[int] = None

class DriverHoldResponse(BaseModel):
    id: int
    driver_id: int
    driver_name: str
    reason: str
    description: str
    status: str
    created_by: int
    created_at: str
    resolved_by: Optional[int] = None
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None

class ClockInWithStockRequest(BaseModel):
    lat: float
    lng: float
    location_name: Optional[str] = None
    scanned_uids: List[str]  # Required stock verification

class ClockInResponse(BaseModel):
    shift_id: int
    clock_in_at: str
    assignment_id: int
    lorry_id: str
    stock_verification_required: bool
    stock_verification_completed: bool
    variance_detected: bool
    message: str


# Admin endpoints for lorry assignment
@router.post("/assignments", response_model=dict)
async def create_lorry_assignment(
    request: LorryAssignmentRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Assign a lorry to a driver for a specific date"""
    try:
        assignment_date = datetime.strptime(request.assignment_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Check if driver exists
    driver = db.get(Driver, request.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Check for existing assignment for this driver on this date
    existing = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == request.driver_id,
                LorryAssignment.assignment_date == assignment_date
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Driver already has lorry assignment for {request.assignment_date}"
        )
    
    # Create assignment
    assignment = LorryAssignment(
        driver_id=request.driver_id,
        lorry_id=request.lorry_id,
        assignment_date=assignment_date,
        assigned_by=current_user.id,
        notes=request.notes,
        status="ASSIGNED"
    )
    
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    
    # Log audit action
    log_action(
        db, 
        user_id=current_user.id, 
        action="LORRY_ASSIGN", 
        resource_type="lorry_assignment", 
        resource_id=assignment.id,
        details={
            "driver_id": request.driver_id,
            "lorry_id": request.lorry_id,
            "assignment_date": request.assignment_date
        }
    )
    
    response = LorryAssignmentResponse(
        id=assignment.id,
        driver_id=assignment.driver_id,
        driver_name=driver.name or f"Driver {driver.id}",
        lorry_id=assignment.lorry_id,
        assignment_date=assignment.assignment_date.strftime("%Y-%m-%d"),
        status=assignment.status,
        stock_verified=assignment.stock_verified,
        stock_verified_at=assignment.stock_verified_at.isoformat() if assignment.stock_verified_at else None,
        shift_id=assignment.shift_id,
        assigned_by=assignment.assigned_by,
        assigned_at=assignment.assigned_at.isoformat(),
        notes=assignment.notes
    )
    
    return envelope(response.model_dump())


@router.get("/assignments", response_model=dict)
async def get_lorry_assignments(
    date: Optional[str] = None,  # YYYY-MM-DD
    driver_id: Optional[int] = None,
    lorry_id: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get lorry assignments with optional filters"""
    query = select(LorryAssignment, Driver).join(Driver, LorryAssignment.driver_id == Driver.id)
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.where(LorryAssignment.assignment_date == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if driver_id:
        query = query.where(LorryAssignment.driver_id == driver_id)
        
    if lorry_id:
        query = query.where(LorryAssignment.lorry_id == lorry_id)
    
    results = db.execute(query.order_by(LorryAssignment.assignment_date.desc())).all()
    
    assignments = []
    for assignment, driver in results:
        assignments.append(LorryAssignmentResponse(
            id=assignment.id,
            driver_id=assignment.driver_id,
            driver_name=driver.name or f"Driver {driver.id}",
            lorry_id=assignment.lorry_id,
            assignment_date=assignment.assignment_date.strftime("%Y-%m-%d"),
            status=assignment.status,
            stock_verified=assignment.stock_verified,
            stock_verified_at=assignment.stock_verified_at.isoformat() if assignment.stock_verified_at else None,
            shift_id=assignment.shift_id,
            assigned_by=assignment.assigned_by,
            assigned_at=assignment.assigned_at.isoformat(),
            notes=assignment.notes
        ).model_dump())
    
    return envelope(assignments)


# Driver endpoints for clock-in with stock verification
@router.get("/my-assignment", response_model=dict)
async def get_my_lorry_assignment(
    date: Optional[str] = None,  # YYYY-MM-DD, defaults to today
    db: Session = Depends(get_session),
    driver = Depends(driver_auth)
):
    """Get driver's lorry assignment for a specific date"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()
    
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver.id,
                LorryAssignment.assignment_date == target_date
            )
        )
    ).scalar_one_or_none()
    
    if not assignment:
        return envelope({"message": "No lorry assignment found for today", "assignment": None})
    
    response = {
        "id": assignment.id,
        "lorry_id": assignment.lorry_id,
        "assignment_date": assignment.assignment_date.strftime("%Y-%m-%d"),
        "status": assignment.status,
        "stock_verified": assignment.stock_verified,
        "stock_verified_at": assignment.stock_verified_at.isoformat() if assignment.stock_verified_at else None,
        "shift_id": assignment.shift_id,
        "notes": assignment.notes
    }
    
    return envelope(response)


@router.post("/clock-in-with-stock", response_model=dict)
async def clock_in_with_stock_verification(
    request: ClockInWithStockRequest,
    db: Session = Depends(get_session),
    driver = Depends(driver_auth)
):
    """Clock in with mandatory stock verification"""
    if not settings.UID_INVENTORY_ENABLED:
        raise HTTPException(status_code=400, detail="UID inventory system is disabled")
    
    # Get today's assignment
    today = date.today()
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver.id,
                LorryAssignment.assignment_date == today
            )
        )
    ).scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="No lorry assignment found for today")
    
    # Check if already clocked in today
    existing_shift = db.execute(
        select(DriverShift).where(
            and_(
                DriverShift.driver_id == driver.id,
                func.date(DriverShift.clock_in_at) == today,
                DriverShift.status == "ACTIVE"
            )
        )
    ).scalar_one_or_none()
    
    if existing_shift:
        raise HTTPException(status_code=409, detail="Already clocked in today")
    
    # Create shift record
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
    
    # Get expected UIDs for this lorry from previous day's verification or initial stock
    expected_uids = await _get_expected_lorry_stock(db, assignment.lorry_id, today)
    
    # Detect variances
    scanned_set = set(request.scanned_uids)
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
        scanned_uids=json.dumps(request.scanned_uids),
        total_scanned=len(request.scanned_uids),
        expected_uids=json.dumps(expected_uids),
        total_expected=len(expected_uids),
        variance_count=variance_count,
        missing_uids=json.dumps(missing_uids),
        unexpected_uids=json.dumps(unexpected_uids),
        status="VERIFIED"
    )
    
    db.add(verification)
    
    # Mark assignment as stock verified
    assignment.stock_verified = True
    assignment.stock_verified_at = now
    
    # Handle variance detection and driver holds
    if variance_detected and settings.UID_INVENTORY_ENABLED:
        await _handle_variance_driver_holds(db, assignment, verification, variance_count, missing_uids, unexpected_uids)
    
    db.commit()
    
    # Log audit action
    log_action(
        db, 
        user_id=driver.id, 
        action="CLOCK_IN_WITH_STOCK", 
        resource_type="driver_shift", 
        resource_id=shift.id,
        details={
            "lorry_id": assignment.lorry_id,
            "scanned_uids_count": len(request.scanned_uids),
            "variance_detected": variance_detected
        }
    )
    
    response = ClockInResponse(
        shift_id=shift.id,
        clock_in_at=shift.clock_in_at.isoformat(),
        assignment_id=assignment.id,
        lorry_id=assignment.lorry_id,
        stock_verification_required=True,
        stock_verification_completed=True,
        variance_detected=variance_detected,
        message="Successfully clocked in with stock verification"
    )
    
    return envelope(response.model_dump())


@router.get("/driver-status", response_model=dict)
async def get_driver_status(
    db: Session = Depends(get_session),
    driver = Depends(driver_auth)
):
    """Check if driver has any active holds that prevent work"""
    # Check for active holds
    active_holds = db.execute(
        select(DriverHold).where(
            and_(
                DriverHold.driver_id == driver.id,
                DriverHold.status == "ACTIVE"
            )
        )
    ).scalars().all()
    
    has_active_holds = len(active_holds) > 0
    hold_reasons = [hold.reason for hold in active_holds]
    
    # Check today's assignment and stock verification status
    today = date.today()
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver.id,
                LorryAssignment.assignment_date == today
            )
        )
    ).scalar_one_or_none()
    
    can_access_orders = (
        not has_active_holds and 
        assignment is not None and 
        assignment.stock_verified
    )
    
    status_response = {
        "can_access_orders": can_access_orders,
        "has_active_holds": has_active_holds,
        "hold_reasons": hold_reasons,
        "assignment_status": {
            "has_assignment": assignment is not None,
            "stock_verified": assignment.stock_verified if assignment else False,
            "lorry_id": assignment.lorry_id if assignment else None
        },
        "message": _get_driver_status_message(has_active_holds, assignment, hold_reasons)
    }
    
    return envelope(status_response)


# Driver hold management endpoints
@router.post("/holds", response_model=dict)
async def create_driver_hold(
    request: DriverHoldRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Create a driver hold"""
    # Check if driver exists
    driver = db.get(Driver, request.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Check for existing active hold
    existing_hold = db.execute(
        select(DriverHold).where(
            and_(
                DriverHold.driver_id == request.driver_id,
                DriverHold.status == "ACTIVE"
            )
        )
    ).scalar_one_or_none()
    
    if existing_hold:
        raise HTTPException(status_code=409, detail="Driver already has an active hold")
    
    # Create hold
    hold = DriverHold(
        driver_id=request.driver_id,
        reason=request.reason,
        description=request.description,
        related_assignment_id=request.related_assignment_id,
        created_by=current_user.id,
        status="ACTIVE"
    )
    
    db.add(hold)
    db.commit()
    db.refresh(hold)
    
    # Log audit action
    log_action(
        db, 
        user_id=current_user.id, 
        action="DRIVER_HOLD_CREATE", 
        resource_type="driver_hold", 
        resource_id=hold.id,
        details={
            "driver_id": request.driver_id,
            "reason": request.reason
        }
    )
    
    response = DriverHoldResponse(
        id=hold.id,
        driver_id=hold.driver_id,
        driver_name=driver.name or f"Driver {driver.id}",
        reason=hold.reason,
        description=hold.description,
        status=hold.status,
        created_by=hold.created_by,
        created_at=hold.created_at.isoformat(),
        resolved_by=hold.resolved_by,
        resolved_at=hold.resolved_at.isoformat() if hold.resolved_at else None,
        resolution_notes=hold.resolution_notes
    )
    
    return envelope(response.model_dump())


@router.get("/holds", response_model=dict)
async def get_driver_holds(
    driver_id: Optional[int] = None,
    status: Optional[str] = None,  # ACTIVE, RESOLVED
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get driver holds with optional filters"""
    query = select(DriverHold, Driver).join(Driver, DriverHold.driver_id == Driver.id)
    
    if driver_id:
        query = query.where(DriverHold.driver_id == driver_id)
    
    if status:
        query = query.where(DriverHold.status == status.upper())
    
    results = db.execute(query.order_by(DriverHold.created_at.desc())).all()
    
    holds = []
    for hold, driver in results:
        holds.append(DriverHoldResponse(
            id=hold.id,
            driver_id=hold.driver_id,
            driver_name=driver.name or f"Driver {driver.id}",
            reason=hold.reason,
            description=hold.description,
            status=hold.status,
            created_by=hold.created_by,
            created_at=hold.created_at.isoformat(),
            resolved_by=hold.resolved_by,
            resolved_at=hold.resolved_at.isoformat() if hold.resolved_at else None,
            resolution_notes=hold.resolution_notes
        ).model_dump())
    
    return envelope(holds)


@router.patch("/holds/{hold_id}/resolve", response_model=dict)
async def resolve_driver_hold(
    hold_id: int,
    resolution_notes: str,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Resolve a driver hold"""
    hold = db.get(DriverHold, hold_id)
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")
    
    if hold.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Hold is not active")
    
    hold.status = "RESOLVED"
    hold.resolved_by = current_user.id
    hold.resolved_at = datetime.now()
    hold.resolution_notes = resolution_notes
    
    db.commit()
    
    # Log audit action
    log_action(
        db, 
        user_id=current_user.id, 
        action="DRIVER_HOLD_RESOLVE", 
        resource_type="driver_hold", 
        resource_id=hold.id,
        details={
            "driver_id": hold.driver_id,
            "resolution_notes": resolution_notes
        }
    )
    
    return envelope({"message": "Driver hold resolved successfully"})


# Helper functions
async def _get_expected_lorry_stock(db: Session, lorry_id: str, date: date) -> List[str]:
    """Get expected UIDs for a lorry based on previous day's verification or initial stock"""
    yesterday = date - timedelta(days=1)
    
    # Get yesterday's verification for this lorry
    yesterday_verification = db.execute(
        select(LorryStockVerification)
        .join(LorryAssignment, LorryStockVerification.assignment_id == LorryAssignment.id)
        .where(
            and_(
                LorryAssignment.lorry_id == lorry_id,
                LorryStockVerification.verification_date == yesterday
            )
        )
        .order_by(LorryStockVerification.created_at.desc())
    ).scalar_one_or_none()
    
    if yesterday_verification:
        # Use yesterday's verified stock as expected stock
        return json.loads(yesterday_verification.scanned_uids)
    else:
        # No previous verification found - return empty for now
        # In a real system, this would come from initial lorry stock allocation
        logging.warning(f"No previous verification found for lorry {lorry_id}")
        return []


async def _handle_variance_driver_holds(
    db: Session, 
    assignment: LorryAssignment, 
    verification: LorryStockVerification,
    variance_count: int,
    missing_uids: List[str],
    unexpected_uids: List[str]
):
    """Handle driver holds when stock variance is detected"""
    
    # Get yesterday's assignment for this lorry to identify the previous driver
    yesterday = assignment.assignment_date - timedelta(days=1)
    yesterday_assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.lorry_id == assignment.lorry_id,
                LorryAssignment.assignment_date == yesterday
            )
        )
    ).scalar_one_or_none()
    
    # Create hold for current driver
    current_driver_hold = DriverHold(
        driver_id=assignment.driver_id,
        reason="STOCK_VARIANCE",
        description=f"Stock variance detected during morning verification. "
                   f"Missing: {len(missing_uids)} items, Unexpected: {len(unexpected_uids)} items. "
                   f"Total variance: {variance_count} items.",
        related_assignment_id=assignment.id,
        related_verification_id=verification.id,
        created_by=1,  # System user
        status="ACTIVE"
    )
    db.add(current_driver_hold)
    
    # Create hold for yesterday's driver if found
    if yesterday_assignment:
        yesterday_driver_hold = DriverHold(
            driver_id=yesterday_assignment.driver_id,
            reason="STOCK_VARIANCE",
            description=f"Stock variance detected in lorry {assignment.lorry_id} the next day. "
                       f"May be responsible for missing/extra items. "
                       f"Missing: {len(missing_uids)} items, Unexpected: {len(unexpected_uids)} items.",
            related_assignment_id=yesterday_assignment.id,
            related_verification_id=verification.id,
            created_by=1,  # System user
            status="ACTIVE"
        )
        db.add(yesterday_driver_hold)
        
        logging.info(f"Created holds for both drivers: current {assignment.driver_id} and yesterday {yesterday_assignment.driver_id}")
    else:
        logging.info(f"Created hold for current driver {assignment.driver_id} only - no previous assignment found")
    
    # Log the variance for audit
    log_action(
        db,
        user_id=1,  # System user
        action="STOCK_VARIANCE_DETECTED",
        resource_type="lorry_stock_verification",
        resource_id=verification.id,
        details={
            "lorry_id": assignment.lorry_id,
            "variance_count": variance_count,
            "missing_uids": missing_uids,
            "unexpected_uids": unexpected_uids,
            "current_driver_id": assignment.driver_id,
            "yesterday_driver_id": yesterday_assignment.driver_id if yesterday_assignment else None
        }
    )


def _get_driver_status_message(has_active_holds: bool, assignment: LorryAssignment, hold_reasons: List[str]) -> str:
    """Generate appropriate status message for driver"""
    if has_active_holds:
        reasons_text = ", ".join(hold_reasons)
        return f"Access restricted due to: {reasons_text}. Contact your supervisor."
    
    if assignment is None:
        return "No lorry assignment for today. Contact your dispatcher."
    
    if not assignment.stock_verified:
        return "Please complete stock verification before accessing orders."
    
    return "You can access your orders."