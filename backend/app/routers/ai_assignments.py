"""AI-assisted order assignment endpoints"""

import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.firebase import get_current_admin_user
from app.db import get_session
from app.models.user import User
from app.services.ai_assignment_service import AIAssignmentService


router = APIRouter(prefix="/ai-assignments", tags=["ai-assignments"])


class AssignmentSuggestion(BaseModel):
    order_id: int
    driver_id: int
    driver_name: str
    distance_km: float
    confidence: str
    reasoning: str


class AssignmentSuggestionsResponse(BaseModel):
    suggestions: List[AssignmentSuggestion]
    method: str
    available_drivers_count: int
    pending_orders_count: int
    scheduled_drivers_count: int = 0
    total_drivers_count: int = 0
    ai_reasoning: str = ""


class ApplyAssignmentRequest(BaseModel):
    order_id: int
    driver_id: int


@router.get("/suggestions", response_model=AssignmentSuggestionsResponse)
async def get_assignment_suggestions(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get AI-powered assignment suggestions for pending orders"""
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        ai_service = AIAssignmentService(db, openai_api_key)
        
        result = ai_service.suggest_assignments()
        
        suggestions = [
            AssignmentSuggestion(
                order_id=s["order_id"],
                driver_id=s["driver_id"], 
                driver_name=s["driver_name"],
                distance_km=s["distance_km"],
                confidence=s["confidence"],
                reasoning=s["reasoning"]
            ) for s in result["suggestions"]
        ]
        
        return AssignmentSuggestionsResponse(
            suggestions=suggestions,
            method=result["method"],
            available_drivers_count=result["available_drivers_count"],
            pending_orders_count=result["pending_orders_count"],
            ai_reasoning=result.get("ai_reasoning", "")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assignment suggestions: {str(e)}"
        )


@router.post("/apply")
async def apply_assignment(
    request: ApplyAssignmentRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Apply a suggested assignment using existing manual assignment logic"""
    try:
        # Import here to avoid circular imports
        from app.models.order import Order
        from app.models.trip import Trip
        from app.models.driver import Driver
        from app.services.fcm import notify_order_assigned
        from app.audit import log_action
        
        # Validate order exists
        order = db.get(Order, request.order_id)
        if not order:
            raise HTTPException(404, "Order not found")
        
        # Validate driver exists and is clocked in
        driver = db.get(Driver, request.driver_id)
        if not driver or not driver.is_active:
            raise HTTPException(404, "Driver not found or inactive")
            
        # Check if driver is clocked in
        ai_service = AIAssignmentService(db)
        available_drivers = ai_service.get_available_drivers()
        if not any(d["driver_id"] == request.driver_id for d in available_drivers):
            raise HTTPException(400, "Driver is not currently clocked in")
        
        # Use the same logic as manual assignment (orders.py lines 401-413)
        trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
        if trip:
            if trip.status in {"DELIVERED", "SUCCESS"}:
                raise HTTPException(400, "Delivered orders cannot be reassigned")
            trip.driver_id = driver.id
            trip.status = "ASSIGNED"
        else:
            trip = Trip(order_id=order.id, driver_id=driver.id, status="ASSIGNED")
            db.add(trip)
        
        order.status = "ASSIGNED"
        db.commit()
        db.refresh(trip)
        
        # Same notifications and logging as manual assignment
        log_action(db, current_user, "ai.assign_driver", f"order_id={order.id},driver_id={driver.id}")
        notify_order_assigned(db, driver.id, order)
        
        return {
            "message": f"Order #{order.code or order.id} assigned to {driver.name}",
            "trip_id": trip.id,
            "order_id": request.order_id,
            "driver_id": request.driver_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply assignment: {str(e)}"
        )


@router.get("/available-drivers")
async def get_available_drivers(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get all drivers currently clocked in and available for assignment"""
    try:
        ai_service = AIAssignmentService(db)
        drivers = ai_service.get_available_drivers()
        
        return {
            "available_drivers": drivers,
            "count": len(drivers)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available drivers: {str(e)}"
        )


@router.get("/pending-orders")
async def get_pending_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get all orders pending assignment"""
    try:
        ai_service = AIAssignmentService(db)
        orders = ai_service.get_pending_orders()
        
        return {
            "pending_orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending orders: {str(e)}"
        )