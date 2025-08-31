"""Unified Assignment Workflow - One smooth flow for order assignment"""

import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.firebase import get_current_admin_user
from app.db import get_session
from app.models.user import User
from app.services.unified_assignment_service import UnifiedAssignmentService


router = APIRouter(prefix="/unified-assignments", tags=["unified-assignments"])


class AutoAssignResponse(BaseModel):
    success: bool
    message: str
    assigned_count: int
    routes_created: int
    assignments: List[Dict[str, Any]]
    routes: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    method: str


class OnHoldOrderResponse(BaseModel):
    order_id: int
    order_code: str
    customer_name: str
    customer_phone: str = None
    address: str = None
    total: float
    created_at: str = None
    on_hold_reason: str


class HandleOnHoldRequest(BaseModel):
    order_id: int
    customer_available: bool
    delivery_date: str = None


class ManualEditSummaryResponse(BaseModel):
    date: str
    routes_count: int
    total_orders: int
    routes: List[Dict[str, Any]]


@router.post("/auto-assign", response_model=AutoAssignResponse)
async def auto_assign_all_new_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Main automation: Auto-assign all new orders using smart assignment and create routes"""
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        service = UnifiedAssignmentService(db, openai_api_key)
        
        result = service.auto_assign_new_orders()
        
        return AutoAssignResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-assign orders: {str(e)}"
        )


@router.get("/on-hold-orders")
async def get_on_hold_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get orders that are on hold and need customer delivery date input"""
    try:
        service = UnifiedAssignmentService(db)
        orders = service.get_on_hold_orders()
        
        return {
            "on_hold_orders": [OnHoldOrderResponse(**order) for order in orders],
            "count": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get on-hold orders: {str(e)}"
        )


@router.post("/handle-on-hold")
async def handle_on_hold_response(
    request: HandleOnHoldRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Handle driver response to on-hold order: customer said when to deliver?"""
    try:
        service = UnifiedAssignmentService(db)
        
        result = service.handle_on_hold_response(
            request.order_id, 
            request.customer_available, 
            request.delivery_date
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle on-hold response: {str(e)}"
        )


@router.get("/hidden-orders")
async def get_hidden_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get orders that should be hidden from assignment (returned, cancelled, etc.)"""
    try:
        service = UnifiedAssignmentService(db)
        orders = service.get_hidden_orders()
        
        return {
            "hidden_orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hidden orders: {str(e)}"
        )


@router.get("/manual-edit-summary", response_model=ManualEditSummaryResponse)
async def get_manual_edit_summary(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get summary of current assignments for manual editing if needed"""
    try:
        service = UnifiedAssignmentService(db)
        result = service.get_manual_edit_summary()
        
        return ManualEditSummaryResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get manual edit summary: {str(e)}"
        )