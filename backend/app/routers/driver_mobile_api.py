"""
Driver Mobile API - Compatibility layer for driver app endpoints
This router provides the exact API interface expected by the mobile driver app
"""

from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Driver, Order, Trip
from ..utils.responses import envelope

# Import request/response models
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

# Router for driver mobile app compatibility
router = APIRouter(prefix="/driver", tags=["driver-mobile"])

# User info endpoint
@router.get("/me")
async def get_current_user(
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get current driver user info"""
    return {
        "id": driver.id,
        "username": driver.name,
        "role": "driver"
    }

# Re-export drivers endpoints with mobile-friendly routing
@router.get("/jobs")
async def get_mobile_jobs(
    status_filter: str = Query("active", description="active|completed|all"),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver jobs - mobile app compatible"""
    # Call the existing endpoint
    from ..routers.drivers import get_driver_jobs
    return get_driver_jobs(status_filter, driver, db)

@router.get("/jobs/{job_id}")
async def get_mobile_job(
    job_id: str,
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get single job - mobile app compatible"""
    from ..routers.drivers import get_driver_job
    return get_driver_job(job_id, driver, db)

@router.post("/locations")
async def post_mobile_locations(
    locations: List[Dict[str, Any]],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Post location updates - mobile app compatible"""
    from ..routers.drivers import post_driver_locations
    return post_driver_locations(locations, driver, db)

@router.patch("/orders/{order_id}")
async def update_mobile_order_status(
    order_id: int,
    payload: Dict[str, Any],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Update order status - mobile app compatible"""
    # Convert dict to proper schema
    from ..schemas import DriverOrderUpdateIn
    from ..routers.drivers import update_order_status
    
    # Convert payload to proper format
    update_payload = DriverOrderUpdateIn(
        status=payload.get("status"),
        uid_actions=payload.get("uid_actions", [])
    )
    
    return update_order_status(order_id, update_payload, driver, db)

@router.post("/orders/{order_id}/pod-photo")
async def upload_mobile_pod_photo(
    order_id: int,
    file: UploadFile = File(...),
    photo_number: int = Query(1),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Upload POD photo - mobile app compatible"""
    from ..routers.drivers import upload_pod_photo
    return upload_pod_photo(order_id, file, photo_number, driver, db)

@router.get("/orders")
async def get_mobile_orders(
    month: Optional[str] = Query(None),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver orders - mobile app compatible"""
    from ..routers.drivers import list_assigned_orders
    return list_assigned_orders(month, driver, db)

@router.get("/commissions")
async def get_mobile_commissions(
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver commissions - mobile app compatible"""
    from ..routers.drivers import my_commissions
    return my_commissions(driver, db)

@router.get("/upsell-incentives")
async def get_mobile_upsell_incentives(
    month: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get upsell incentives - mobile app compatible"""
    from ..routers.drivers import my_upsell_incentives
    return my_upsell_incentives(month, status, driver, db)

# Shift management endpoints
@router.post("/shifts/clock-in")
async def mobile_clock_in(
    request: ClockInRequest,
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Intelligent clock in - automatically uses stock verification if driver has lorry assignment"""
    from ..models.lorry_assignment import LorryAssignment
    from sqlalchemy import select, and_, func
    from datetime import date
    
    # Check if driver has lorry assignment today
    today = date.today()
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver.id,
                LorryAssignment.assignment_date == today
            )
        )
    ).scalar_one_or_none()
    
    # ALL drivers must have lorry assignment - no exceptions
    if not assignment:
        raise HTTPException(
            status_code=400, 
            detail="No lorry assignment found for today. Please wait for lorry assignment from dispatcher."
        )
    
    if assignment.status not in ["ASSIGNED", "ACTIVE"]:
        raise HTTPException(
            status_code=400,
            detail=f"Lorry assignment status is {assignment.status}. Please contact dispatcher."
        )
    
    # Driver has valid lorry assignment - use stock verification clock-in
    from ..routers.lorry_management import clock_in_with_stock_verification
    
    # Convert ClockInRequest to ClockInWithStockRequest
    stock_request_data = {
        "lat": request.lat,
        "lng": request.lng,
        "location_name": request.location_name,
        "scanned_uids": request.scanned_uids or []
    }
    
    # Create ClockInWithStockRequest from lorry_management
    from ..routers.lorry_management import ClockInWithStockRequest
    stock_request = ClockInWithStockRequest(**stock_request_data)
    
    return await clock_in_with_stock_verification(stock_request, db, driver)

@router.post("/shifts/clock-out")
async def mobile_clock_out(
    request: ClockOutRequest,
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Clock out - mobile app compatible"""
    from ..routers.shifts import clock_out
    return await clock_out(request, driver, db)

@router.get("/shifts/status")
async def mobile_shift_status(
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get shift status - mobile app compatible"""
    from ..routers.shifts import get_shift_status
    return await get_shift_status(driver, db)

@router.get("/shifts/active")
async def mobile_active_shift(
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get active shift - mobile app compatible"""
    from ..routers.shifts import get_active_shift
    return await get_active_shift(driver, db)

@router.get("/shifts/history")
async def mobile_shift_history(
    limit: int = Query(10),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get shift history - mobile app compatible"""
    from ..routers.shifts import get_shift_history
    return await get_shift_history(limit, driver, db)

# Inventory endpoints
@router.get("/inventory/config")
async def mobile_inventory_config():
    """Get inventory config - mobile app compatible"""
    from ..routers.inventory import get_inventory_config
    return await get_inventory_config()

@router.post("/inventory/uid/scan")
async def mobile_uid_scan(
    request: Dict[str, Any],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Scan UID - mobile app compatible"""
    from ..routers.inventory import scan_uid_endpoint
    return await scan_uid_endpoint(request, db)

@router.get("/inventory/lorry/{driver_id}/stock")
async def mobile_lorry_stock(
    driver_id: int,
    date: str = Query(...),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get lorry stock - mobile app compatible"""
    from ..routers.drivers import get_driver_lorry_stock
    return get_driver_lorry_stock(driver_id, date, db, driver)

@router.post("/inventory/lorry/{driver_id}/stock/upload")
async def mobile_lorry_stock_upload(
    driver_id: int,
    body: Dict[str, Any],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Upload lorry stock - mobile app compatible"""
    # TODO: Implement stock upload functionality
    return {"error": "Stock upload functionality not implemented", "status": "not_implemented"}

@router.post("/inventory/sku/resolve")
async def mobile_sku_resolve(
    request: Dict[str, Any],
    db: Session = Depends(get_session)
):
    """Resolve SKU - mobile app compatible"""
    from ..routers.inventory import resolve_sku
    return await resolve_sku(request, db)

# Order management
@router.post("/orders/simple")
async def mobile_create_order(
    request: Dict[str, Any],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Create simple order - mobile app compatible"""
    # Implementation would depend on your order creation logic
    # This is a placeholder for the mobile app's simple order creation
    return envelope({
        "success": True,
        "message": "Order creation not yet implemented",
        "order_id": None
    })

# Lorry management
@router.get("/lorry-management/my-assignment")
async def mobile_my_assignment(
    date: Optional[str] = Query(None),
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get my lorry assignment - mobile app compatible"""
    from ..routers.lorry_management import get_my_lorry_assignment
    return await get_my_lorry_assignment(date, db, driver)

@router.post("/lorry-management/clock-in-with-stock")
async def mobile_clock_in_with_stock(
    request: Dict[str, Any],
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Clock in with stock verification - mobile app compatible"""
    from ..routers.lorry_management import clock_in_with_stock_verification
    return await clock_in_with_stock_verification(request, driver, db)

@router.get("/lorry-management/driver-status")
async def mobile_driver_status(
    driver: Driver = Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Get driver status - mobile app compatible"""
    from ..routers.lorry_management import get_driver_status
    return await get_driver_status(db, driver)