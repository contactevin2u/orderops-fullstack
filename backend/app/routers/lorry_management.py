from datetime import datetime, date, timedelta
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
from ..models import (
    Lorry,
    LorryAssignment, 
    LorryStockVerification, 
    DriverHold, 
    Driver, 
    DriverShift, 
    Item,
    User,
    LorryStockTransaction
)
from ..auth.deps import require_roles, Role, get_current_user
from ..auth.firebase import driver_auth
from ..core.config import settings
from ..utils.responses import envelope
from ..utils.audit import log_action
from ..services.lorry_inventory_service import LorryInventoryService
from ..services.lorry_assignment_service import LorryAssignmentService


router = APIRouter(
    prefix="/lorry-management",
    tags=["lorry-management"],
)

logger = logging.getLogger(__name__)


async def parse_json_request(request: Request) -> dict:
    """Parse JSON request from either JSON object or JSON string"""
    try:
        # First try to get as normal JSON
        body = await request.json()
        return body
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
            return body_dict
        except Exception as parse_error:
            logger.error(f"Failed to parse request body: {parse_error}")
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid request format. Expected JSON object or valid JSON string. Error: {str(parse_error)}"
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


# REMOVED: Manual assignment endpoint
# Use /auto-assign endpoint instead for all lorry assignments


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
        target_date = datetime.now().date()
    
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
    
    assignment_data = {
        "id": assignment.id,
        "lorry_id": assignment.lorry_id,
        "assignment_date": assignment.assignment_date.strftime("%Y-%m-%d"),
        "status": assignment.status,
        "stock_verified": assignment.stock_verified,
        "stock_verified_at": assignment.stock_verified_at.isoformat() if assignment.stock_verified_at else None,
        "shift_id": assignment.shift_id,
        "notes": assignment.notes
    }
    
    response = {
        "message": f"Assignment found for lorry {assignment.lorry_id}",
        "assignment": assignment_data
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
    
    # Create shift record using ShiftService for proper working hours tracking
    from ..services.shift_service import ShiftService
    shift_service = ShiftService(db)
    shift = shift_service.clock_in(
        driver_id=driver.id,
        lat=request.lat,
        lng=request.lng,
        location_name=request.location_name
    )
    
    db.flush()  # Ensure shift ID is available
    
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
    
    # Return standard ShiftResponse for compatibility with clock-out
    from ..routers.shifts import ShiftResponse
    shift_response = ShiftResponse.from_model(shift)
    
    # Add stock verification info to the response
    response_data = shift_response.model_dump()
    response_data.update({
        "assignment_id": assignment.id,
        "lorry_id": assignment.lorry_id,
        "stock_verification_required": True,
        "stock_verification_completed": True,
        "variance_detected": variance_detected,
        "variance_count": variance_count,
        "total_scanned": len(request.scanned_uids),
        "total_expected": len(expected_uids),
        "message": f"Successfully clocked in with stock verification. {variance_count} variance(s) detected." if variance_detected else "Successfully clocked in with stock verification. No variances detected."
    })
    
    return envelope(response_data)


@router.get("/driver-status", response_model=dict)
async def get_driver_status(
    db: Session = Depends(get_session),
    driver = Depends(driver_auth)
):
    """Check if driver has any active holds that prevent work"""
    
    # Check for active holds
    active_holds = db.query(DriverHold).filter(
        DriverHold.driver_id == driver.id,
        DriverHold.status == "ACTIVE"
    ).all()
    
    has_active_holds = len(active_holds) > 0
    hold_reasons = [hold.reason for hold in active_holds]
    
    # Check today's assignment and stock verification status
    today = date.today()
    assignment = db.query(LorryAssignment).filter(
        LorryAssignment.driver_id == driver.id,
        LorryAssignment.assignment_date == today
    ).first()
    
    # ALL drivers must have lorry assignment and complete stock verification
    can_access_orders = (
        not has_active_holds and 
        assignment is not None and 
        assignment.status in ["ASSIGNED", "ACTIVE"] and
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
    
    return status_response


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


class ResolveHoldRequest(BaseModel):
    resolution_notes: str

@router.patch("/holds/{hold_id}/resolve", response_model=dict)
async def resolve_driver_hold(
    hold_id: int,
    request: ResolveHoldRequest,
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
    hold.resolution_notes = request.resolution_notes
    
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
            "resolution_notes": request.resolution_notes
        }
    )
    
    return envelope({"message": "Driver hold resolved successfully"})


# Helper functions
async def _get_expected_lorry_stock(db: Session, lorry_id: str, date: date) -> List[str]:
    """Get expected UIDs for a lorry based on admin stock transactions and deliveries"""
    # Use the new inventory service to get real-time stock
    inventory_service = LorryInventoryService(db)
    
    # Get stock as of end of previous day to account for overnight changes
    previous_day = date - timedelta(days=1)
    expected_stock = inventory_service.get_current_stock(lorry_id, previous_day)
    
    # If no stock found, check if this is a valid "empty lorry" scenario
    if not expected_stock:
        # Check if there are any historical transactions for this lorry
        has_history = inventory_service.has_transaction_history(lorry_id)
        if not has_history:
            logging.info(f"New lorry {lorry_id} with no history - empty start is expected")
        else:
            logging.info(f"Existing lorry {lorry_id} should be empty on {date}")
    
    logging.info(f"Expected stock for lorry {lorry_id} on {date}: {len(expected_stock)} items")
    return expected_stock


async def _handle_variance_driver_holds(
    db: Session, 
    assignment: LorryAssignment, 
    verification: LorryStockVerification,
    variance_count: int,
    missing_uids: List[str],
    unexpected_uids: List[str]
):
    """Handle driver holds when stock variance is detected - Enhanced Dual-Hold System"""
    
    # ENHANCED: Find the last driver who actually performed stock actions on this lorry
    # Look for any stock action (LOAD, UNLOAD, DELIVERY, COLLECTION, REPAIR, TRANSFER, etc.)
    # regardless of how many days ago it occurred
    last_action_transaction = db.execute(
        select(LorryStockTransaction).where(
            and_(
                LorryStockTransaction.lorry_id == assignment.lorry_id,
                LorryStockTransaction.driver_id.isnot(None),  # Must have a driver
                LorryStockTransaction.action.in_([
                    "LOAD", "UNLOAD", "DELIVERY", "COLLECTION", 
                    "REPAIR", "TRANSFER", "ADMIN_ADJUSTMENT"
                ])
            )
        ).order_by(LorryStockTransaction.transaction_date.desc())
    ).first()
    
    # Create hold for current driver (scanner)
    current_driver_hold = DriverHold(
        driver_id=assignment.driver_id,
        reason="STOCK_VARIANCE_SCANNER",
        description=f"Stock variance detected during verification scan. "
                   f"Missing: {len(missing_uids)} items, Unexpected: {len(unexpected_uids)} items. "
                   f"Total variance: {variance_count} items. Role: Scanning driver.",
        related_assignment_id=assignment.id,
        related_verification_id=verification.id,
        created_by=1,  # System user
        status="ACTIVE"
    )
    db.add(current_driver_hold)
    
    # Create hold for last action driver if found and different from current driver
    last_action_driver_id = None
    if last_action_transaction and last_action_transaction.driver_id != assignment.driver_id:
        last_action_driver_id = last_action_transaction.driver_id
        
        # Get the assignment that was active when this transaction occurred
        last_action_assignment = db.execute(
            select(LorryAssignment).where(
                and_(
                    LorryAssignment.lorry_id == assignment.lorry_id,
                    LorryAssignment.driver_id == last_action_driver_id,
                    LorryAssignment.assignment_date <= last_action_transaction.transaction_date.date()
                )
            ).order_by(LorryAssignment.assignment_date.desc())
        ).first()
        
        last_action_driver_hold = DriverHold(
            driver_id=last_action_driver_id,
            reason="STOCK_VARIANCE_LAST_ACTION",
            description=f"Stock variance detected in lorry {assignment.lorry_id}. "
                       f"Last performed stock action: {last_action_transaction.action} on "
                       f"{last_action_transaction.transaction_date.strftime('%Y-%m-%d %H:%M')}. "
                       f"Missing: {len(missing_uids)} items, Unexpected: {len(unexpected_uids)} items. "
                       f"Role: Last action driver.",
            related_assignment_id=last_action_assignment.id if last_action_assignment else None,
            related_verification_id=verification.id,
            created_by=1,  # System user
            status="ACTIVE"
        )
        db.add(last_action_driver_hold)
        
        logging.info(f"Dual-Hold System: Created holds for scanner driver {assignment.driver_id} "
                    f"and last action driver {last_action_driver_id} "
                    f"(action: {last_action_transaction.action} on {last_action_transaction.transaction_date})")
    else:
        if last_action_transaction:
            logging.info(f"Dual-Hold System: Scanner {assignment.driver_id} is same as last action driver "
                        f"(action: {last_action_transaction.action}), created single hold")
        else:
            logging.info(f"Dual-Hold System: No previous stock actions found for lorry {assignment.lorry_id}, "
                        f"created hold for scanner driver {assignment.driver_id} only")
    
    # Log the variance for audit with enhanced dual-hold details
    log_action(
        db,
        user_id=1,  # System user
        action="STOCK_VARIANCE_DETECTED_DUAL_HOLD",
        resource_type="lorry_stock_verification",
        resource_id=verification.id,
        details={
            "lorry_id": assignment.lorry_id,
            "variance_count": variance_count,
            "missing_uids": missing_uids,
            "unexpected_uids": unexpected_uids,
            "scanner_driver_id": assignment.driver_id,
            "last_action_driver_id": last_action_driver_id,
            "last_action_type": last_action_transaction.action if last_action_transaction else None,
            "last_action_date": last_action_transaction.transaction_date.isoformat() if last_action_transaction else None,
            "dual_hold_applied": last_action_driver_id is not None,
            "hold_system": "ENHANCED_DUAL_HOLD_V2"
        }
    )


def _get_driver_status_message(has_active_holds: bool, assignment: LorryAssignment, hold_reasons: List[str]) -> str:
    """Generate appropriate status message for driver"""
    if has_active_holds:
        reasons_text = ", ".join(hold_reasons)
        return f"Access restricted due to: {reasons_text}. Contact your supervisor."
    
    if assignment is None:
        return "Please wait for lorry assignment from dispatcher. All drivers require daily lorry assignment."
    
    if assignment.status not in ["ASSIGNED", "ACTIVE"]:
        return f"Lorry assignment status is {assignment.status}. Contact your dispatcher."
    
    if not assignment.stock_verified:
        return "Please complete stock verification before accessing orders."
    
    return "You can access your orders."


# Admin Stock Management Models
class LoadStockRequest(BaseModel):
    uids: List[str]
    notes: Optional[str] = None

class UnloadStockRequest(BaseModel):
    uids: List[str]
    notes: Optional[str] = None

class StockOperationResponse(BaseModel):
    success: bool
    message: str
    processed_count: int
    errors: List[str] = []

class LorryInventoryResponse(BaseModel):
    lorry_id: str
    current_stock: List[str]
    total_count: int
    as_of_date: str

class StockTransactionResponse(BaseModel):
    id: int
    lorry_id: str
    action: str
    uid: str
    admin_user: str
    notes: Optional[str]
    transaction_date: str
    created_at: str

# Lorry Management Models
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
    current_location: Optional[str]
    last_maintenance_date: Optional[str]
    created_at: str
    updated_at: str

class UpdateDriverPriorityRequest(BaseModel):
    priority_lorry_id: Optional[str] = None

class UpdatePriorityLorryRequest(BaseModel):
    priority_lorry_id: Optional[str] = None

class AutoAssignRequest(BaseModel):
    assignment_date: str  # YYYY-MM-DD

class AssignmentStatusResponse(BaseModel):
    assignment_date: str
    scheduled_drivers: int
    assigned_drivers: int
    unassigned_drivers: int
    available_lorries: int
    can_auto_assign: bool
    assignments: List[Dict[str, Any]]


# Admin Stock Management Endpoints

@router.post("/stock/{lorry_id}/load", response_model=dict)
async def load_lorry_stock(
    lorry_id: str,
    raw_request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Admin loads UIDs into a lorry"""
    logger.info(f"=== STOCK LOAD DEBUG START === lorry_id: {lorry_id}")
    
    try:
        # Parse JSON with robust handling
        body = await parse_json_request(raw_request)
        logger.info(f"DEBUG: Parsed request body: {body}")
        
        request = LoadStockRequest(**body)
        logger.info(f"DEBUG: LoadStockRequest created - uids count: {len(request.uids)}, notes: {request.notes}")
        
        inventory_service = LorryInventoryService(db)
        logger.info(f"DEBUG: LorryInventoryService created")
        
        result = inventory_service.load_uids(
            lorry_id=lorry_id,
            uids=request.uids,
            admin_user_id=current_user.id,
            notes=request.notes
        )
        logger.info(f"DEBUG: inventory_service.load_uids result: {result}")
    except Exception as e:
        logger.error(f"DEBUG: Exception in load_lorry_stock: {e}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        raise
    
    # Log audit action
    logger.info(f"DEBUG: About to log audit action")
    log_action(
        db, 
        user_id=current_user.id, 
        action="LORRY_STOCK_LOAD", 
        resource_type="lorry_stock", 
        resource_id=lorry_id,
        details={
            "uids_count": len(request.uids),
            "loaded_count": result["loaded_count"],
            "errors_count": len(result["errors"])
        }
    )
    logger.info(f"DEBUG: Audit action logged successfully")
    
    logger.info(f"=== STOCK LOAD DEBUG END === returning result: {result}")
    return envelope(result)


@router.post("/stock/{lorry_id}/unload", response_model=dict)
async def unload_lorry_stock(
    lorry_id: str,
    raw_request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Admin unloads UIDs from a lorry"""
    # Parse JSON with robust handling
    body = await parse_json_request(raw_request)
    request = UnloadStockRequest(**body)
    
    inventory_service = LorryInventoryService(db)
    
    result = inventory_service.unload_uids(
        lorry_id=lorry_id,
        uids=request.uids,
        admin_user_id=current_user.id,
        notes=request.notes
    )
    
    # Log audit action
    log_action(
        db, 
        user_id=current_user.id, 
        action="LORRY_STOCK_UNLOAD", 
        resource_type="lorry_stock", 
        resource_id=lorry_id,
        details={
            "uids_count": len(request.uids),
            "unloaded_count": result["unloaded_count"],
            "errors_count": len(result["errors"])
        }
    )
    
    return envelope(result)


@router.get("/stock/{lorry_id}", response_model=dict)
async def get_lorry_current_stock(
    lorry_id: str,
    as_of_date: Optional[str] = None,  # YYYY-MM-DD
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get current stock in a lorry"""
    inventory_service = LorryInventoryService(db)
    
    target_date = None
    if as_of_date:
        try:
            target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    current_stock = inventory_service.get_current_stock(lorry_id, target_date)
    
    response = LorryInventoryResponse(
        lorry_id=lorry_id,
        current_stock=current_stock,
        total_count=len(current_stock),
        as_of_date=(target_date or date.today()).strftime("%Y-%m-%d")
    )
    
    return envelope(response.model_dump())


@router.get("/stock/transactions", response_model=dict)
async def get_stock_transactions(
    lorry_id: Optional[str] = None,
    start_date: Optional[str] = None,  # YYYY-MM-DD
    end_date: Optional[str] = None,    # YYYY-MM-DD
    date: Optional[str] = None,        # YYYY-MM-DD (single date filter for convenience)
    limit: int = 100,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get stock transaction history"""
    logger.info(f"=== STOCK TRANSACTIONS DEBUG START === lorry_id: {lorry_id}, start_date: {start_date}, end_date: {end_date}, date: {date}, limit: {limit}")
    
    try:
        inventory_service = LorryInventoryService(db)
        logger.info(f"DEBUG: LorryInventoryService created")
    except Exception as e:
        logger.error(f"DEBUG: Error creating inventory service: {e}")
        raise
    
    start_date_obj = None
    end_date_obj = None
    
    # Handle single date parameter (convenience for frontend)
    if date and not start_date and not end_date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            start_date_obj = date_obj
            end_date_obj = date_obj
            logger.info(f"DEBUG: Using single date filter: {date_obj}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    try:
        transactions = inventory_service.get_stock_transactions(
            lorry_id=lorry_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            limit=limit
        )
        logger.info(f"DEBUG: get_stock_transactions returned {len(transactions) if isinstance(transactions, list) else type(transactions)} items")
        logger.info(f"DEBUG: First few transactions: {transactions[:3] if isinstance(transactions, list) and len(transactions) > 0 else transactions}")
    except Exception as e:
        logger.error(f"DEBUG: Error getting stock transactions: {e}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        raise
    
    logger.info(f"=== STOCK TRANSACTIONS DEBUG END === returning {len(transactions) if isinstance(transactions, list) else type(transactions)} transactions")
    return envelope(transactions)


@router.get("/stock/summary", response_model=dict)
async def get_all_lorries_inventory_summary(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get summary of all lorry inventories"""
    logger.info(f"=== STOCK SUMMARY DEBUG START ===")
    
    try:
        inventory_service = LorryInventoryService(db)
        logger.info(f"DEBUG: LorryInventoryService created")
        
        summary = inventory_service.get_lorry_inventory_summary()
        logger.info(f"DEBUG: get_lorry_inventory_summary returned: {summary}")
        logger.info(f"DEBUG: Summary type: {type(summary)}")
        
        if isinstance(summary, list):
            logger.info(f"DEBUG: Summary list length: {len(summary)}")
        elif isinstance(summary, dict):
            logger.info(f"DEBUG: Summary dict keys: {summary.keys()}")
            
    except Exception as e:
        logger.error(f"DEBUG: Error in stock summary: {e}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        raise
        
    logger.info(f"=== STOCK SUMMARY DEBUG END === returning summary")
    return envelope(summary)


# Lorry Management Endpoints

@router.post("/lorries", response_model=dict)
async def create_lorry(
    raw_request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Create a new lorry"""
    # Parse JSON with robust handling
    body = await parse_json_request(raw_request)
    request = CreateLorryRequest(**body)
    
    assignment_service = LorryAssignmentService(db)
    
    result = assignment_service.create_lorry(
        lorry_id=request.lorry_id,
        plate_number=request.plate_number,
        model=request.model,
        capacity=request.capacity,
        base_warehouse=request.base_warehouse,
        notes=request.notes
    )
    
    if result["success"]:
        # Log audit action
        log_action(
            db, 
            user_id=current_user.id, 
            action="LORRY_CREATE", 
            resource_type="lorry", 
            resource_id=result["lorry"]["id"] if result["lorry"] else None,
            details={
                "lorry_id": request.lorry_id,
                "base_warehouse": request.base_warehouse
            }
        )
    
    return envelope(result)


@router.get("/lorries", response_model=dict)
async def get_all_lorries(
    include_inactive: bool = False,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get all lorries"""
    assignment_service = LorryAssignmentService(db)
    lorries = assignment_service.get_all_lorries(include_inactive=include_inactive)
    
    return envelope({
        "lorries": lorries,
        "total_count": len(lorries)
    })


@router.patch("/drivers/{driver_id}/priority-lorry", response_model=dict)
async def update_driver_priority_lorry(
    driver_id: int,
    raw_request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Update driver's priority lorry"""
    # Parse JSON with robust handling
    body = await parse_json_request(raw_request)
    request = UpdateDriverPriorityRequest(**body)
    
    assignment_service = LorryAssignmentService(db)
    
    result = assignment_service.update_driver_priority_lorry(
        driver_id=driver_id,
        priority_lorry_id=request.priority_lorry_id
    )
    
    if result["success"]:
        # Log audit action
        log_action(
            db, 
            user_id=current_user.id, 
            action="DRIVER_PRIORITY_LORRY_UPDATE", 
            resource_type="driver", 
            resource_id=driver_id,
            details={
                "priority_lorry_id": request.priority_lorry_id
            }
        )
    
    return envelope(result)


@router.post("/auto-assign", response_model=dict)
async def auto_assign_lorries(
    raw_request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Automatically assign lorries to scheduled drivers"""
    try:
        # Parse the request using our robust parser
        body = await parse_json_request(raw_request)
        request = AutoAssignRequest(**body)
        
        assignment_date = datetime.strptime(request.assignment_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error parsing auto-assign request: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid request format: {str(e)}")
    
    assignment_service = LorryAssignmentService(db)
    
    result = assignment_service.auto_assign_lorries_for_date(
        assignment_date=assignment_date,
        admin_user_id=current_user.id
    )
    
    if result["success"] and result["assignments_created"] > 0:
        # Log audit action
        log_action(
            db, 
            user_id=current_user.id, 
            action="LORRY_AUTO_ASSIGN", 
            resource_type="lorry_assignment", 
            resource_id=None,
            details={
                "assignment_date": request.assignment_date,
                "assignments_created": result["assignments_created"]
            }
        )
    
    return envelope(result)


@router.get("/assignment-status", response_model=dict)
async def get_lorry_assignment_status(
    date: Optional[str] = None,  # YYYY-MM-DD, defaults to today
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get assignment status and statistics for a specific date"""
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    
    assignment_service = LorryAssignmentService(db)
    status = assignment_service.get_assignment_status_for_date(target_date)
    
    return envelope(status)


@router.get("/drivers", response_model=dict)
async def get_drivers_with_priority_lorries(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get all active drivers with their priority lorry assignments"""
    drivers = db.execute(
        select(Driver).where(Driver.is_active == True).order_by(Driver.name, Driver.id)
    ).scalars().all()
    
    driver_list = []
    for driver in drivers:
        driver_list.append({
            "id": driver.id,
            "name": driver.name or f"Driver {driver.id}",
            "phone": driver.phone,
            "base_warehouse": driver.base_warehouse,
            "priority_lorry_id": driver.priority_lorry_id,
            "created_at": driver.created_at.isoformat()
        })
    
    return envelope({
        "drivers": driver_list,
        "total_count": len(driver_list)
    })


@router.post("/test-validation")
async def test_validation(
    request: CreateLorryRequest,
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Test endpoint to debug validation issues"""
    return envelope({
        "message": "Validation successful",
        "request_data": request.dict(),
        "user": getattr(current_user, 'username', getattr(current_user, 'email', 'unknown'))
    })


@router.get("/status")
async def get_status(
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Get basic status for lorry management"""
    try:
        from ..models import Lorry
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


@router.get("/debug/table-check")
async def debug_table_check(
    current_user = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_session)
):
    """Debug endpoint to check if required tables exist"""
    try:
        from sqlalchemy import text, inspect
        
        logger.info("DEBUG: === POSTGRESQL TABLE CHECK START ===")
        logger.info(f"DEBUG: Database URL type: {type(db.bind.url)}")
        logger.info(f"DEBUG: Database dialect: {db.bind.dialect.name}")
        
        # Check if lorry_stock_transactions table exists (PostgreSQL version)
        table_exists = False
        transaction_count = 0
        table_columns = []
        
        try:
            # Use PostgreSQL system tables to check if table exists
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'lorry_stock_transactions')"
            )).fetchone()
            table_exists = result[0] if result else False
            logger.info(f"DEBUG: lorry_stock_transactions table exists: {table_exists}")
            
            if table_exists:
                # Get table structure
                columns_result = db.execute(text(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'lorry_stock_transactions' ORDER BY ordinal_position"
                )).fetchall()
                table_columns = [f"{row[0]}:{row[1]}({'NULL' if row[2]=='YES' else 'NOT NULL'})" for row in columns_result]
                logger.info(f"DEBUG: Table columns: {table_columns}")
                
                # Get record count
                try:
                    count_result = db.execute(text("SELECT COUNT(*) FROM lorry_stock_transactions")).fetchone()
                    transaction_count = count_result[0] if count_result else 0
                    logger.info(f"DEBUG: Transaction count in table: {transaction_count}")
                    
                    # Get sample records if any exist
                    if transaction_count > 0:
                        sample_result = db.execute(text("SELECT lorry_id, action, uid, admin_user_id, transaction_date FROM lorry_stock_transactions ORDER BY created_at DESC LIMIT 3")).fetchall()
                        logger.info(f"DEBUG: Sample transactions: {[dict(row._mapping) for row in sample_result]}")
                    
                except Exception as e:
                    logger.error(f"DEBUG: Error querying table data: {e}")
            
        except Exception as e:
            logger.error(f"DEBUG: Error checking table existence: {e}")
        
        # Check if LorryStockTransaction model can be imported
        model_importable = False
        model_error = None
        try:
            from ..models import LorryStockTransaction
            model_importable = True
            logger.info("DEBUG: LorryStockTransaction model imported successfully")
            
            # Try to create a simple query using the model
            test_query = db.query(LorryStockTransaction).limit(1)
            logger.info(f"DEBUG: Model query created: {str(test_query)}")
            
        except Exception as e:
            model_error = str(e)
            logger.error(f"DEBUG: Error importing/using LorryStockTransaction model: {e}")
        
        # List all tables to see what's available
        all_tables = []
        try:
            inspector = inspect(db.bind)
            all_tables = inspector.get_table_names()
            logger.info(f"DEBUG: All tables in database: {all_tables[:20]}..." if len(all_tables) > 20 else f"DEBUG: All tables in database: {all_tables}")
        except Exception as e:
            logger.error(f"DEBUG: Error listing all tables: {e}")
        
        result_data = {
            "database_type": db.bind.dialect.name,
            "table_exists": table_exists,
            "model_importable": model_importable,
            "model_error": model_error,
            "transaction_count": transaction_count,
            "table_columns": table_columns,
            "total_tables_count": len(all_tables),
            "sample_table_names": all_tables[:10] if all_tables else [],
            "message": "PostgreSQL table check completed"
        }
        
        logger.info(f"DEBUG: === POSTGRESQL TABLE CHECK END === Result: {result_data}")
        return envelope(result_data)
        
    except Exception as e:
        logger.error(f"DEBUG: Error in table check: {e}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking table: {str(e)}"
        )


# REMOVED: Duplicate clock-in-with-stock endpoint (line 313 is the primary)