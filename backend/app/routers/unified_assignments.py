"""Unified Assignment Workflow - One smooth flow for order assignment"""

import os
from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.auth.firebase import get_current_admin_user
from app.db import get_session
from app.models.user import User
from app.models.order import Order
from app.models.trip import Trip
from app.services.smart_assignment_service import SmartAssignmentService


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
    """Main automation: Auto-assign all new orders using smart assignment"""
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        service = SmartAssignmentService(db, openai_api_key)
        
        result = service.suggest_assignments()
        
        return AutoAssignResponse(
            success=True,
            message=f"Smart assignment suggested {len(result['suggestions'])} assignments",
            assigned_count=len(result["suggestions"]),
            routes_created=0,
            assignments=result["suggestions"],
            routes=[],
            failed=[],
            method=result["method"]
        )
        
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
        # Get orders with ON_HOLD status
        on_hold_orders = db.query(Order).filter(Order.status == "ON_HOLD").all()
        
        orders = []
        for order in on_hold_orders:
            orders.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "customer_phone": order.customer.phone if order.customer else None,
                "address": order.customer.address if order.customer else None,
                "total": float(order.total) if order.total else 0,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "on_hold_reason": order.notes or "Customer requested delivery delay"
            })
        
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
        from datetime import datetime, timedelta
        
        order = db.get(Order, request.order_id)
        if not order:
            raise ValueError(f"Order {request.order_id} not found")
        
        if request.customer_available and request.delivery_date:
            # Customer gave a date - schedule for that date
            try:
                parsed_date = datetime.fromisoformat(request.delivery_date).date()
                order.delivery_date = parsed_date
                order.status = "PENDING"  # Back to pending for assignment
                order.notes = f"Customer requested delivery on {parsed_date.strftime('%B %d, %Y')}"
                
                if parsed_date == date.today():
                    message = f"Order rescheduled for today and ready for assignment"
                else:
                    message = f"Order rescheduled for {parsed_date.strftime('%B %d, %Y')}"
                
            except ValueError:
                raise ValueError("Invalid delivery date format")
        else:
            # Customer said no specific date - retry tomorrow
            tomorrow = datetime.now().date() + timedelta(days=1)
            order.delivery_date = tomorrow
            order.status = "PENDING"
            order.notes = "Customer has no specific date preference, rescheduled for tomorrow"
            message = f"Order rescheduled for tomorrow ({tomorrow.strftime('%B %d, %Y')})"
        
        db.commit()
        
        return {
            "success": True,
            "message": message,
            "order_id": request.order_id,
            "new_status": order.status,
            "new_delivery_date": order.delivery_date.isoformat() if order.delivery_date else None
        }
        
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
        hidden_statuses = ["RETURNED", "CANCELLED", "REFUNDED", "VOID"]
        
        hidden_orders = db.query(Order).filter(Order.status.in_(hidden_statuses)).all()
        
        orders = []
        for order in hidden_orders:
            orders.append({
                "order_id": order.id,
                "order_code": order.code,
                "status": order.status,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "total": float(order.total) if order.total else 0,
                "hidden_reason": f"Order {order.status.lower()}"
            })
        
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
        from app.models.driver_route import DriverRoute
        from app.models.driver import Driver
        
        today = date.today()
        
        # Get today's routes with their orders
        routes = db.query(DriverRoute).filter(DriverRoute.route_date == today).all()
        
        route_summaries = []
        for route in routes:
            # Get trips for this route
            trips = db.query(Trip).filter(Trip.route_id == route.id).all()
            
            orders = []
            for trip in trips:
                order = db.get(Order, trip.order_id)
                if order:
                    orders.append({
                        "order_id": order.id,
                        "order_code": order.code,
                        "customer_name": order.customer.name if order.customer else "Unknown",
                        "status": trip.status,
                        "total": float(order.total) if order.total else 0
                    })
            
            driver = db.get(Driver, route.driver_id)
            route_summaries.append({
                "route_id": route.id,
                "driver_id": route.driver_id,
                "driver_name": driver.name if driver else f"Driver {route.driver_id}",
                "route_name": route.name,
                "orders_count": len(orders),
                "orders": orders,
                "can_add_secondary_driver": route.secondary_driver_id is None
            })
        
        result = {
            "date": today.isoformat(),
            "routes_count": len(route_summaries),
            "total_orders": sum(r["orders_count"] for r in route_summaries),
            "routes": route_summaries
        }
        
        return ManualEditSummaryResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get manual edit summary: {str(e)}"
        )


@router.get("/debug/pending-orders")
async def debug_pending_orders(
    order_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Debug endpoint to troubleshoot order assignment filtering"""
    try:
        today = date.today()
        
        # Get ALL orders with their trip information
        all_orders = (
            db.query(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .all()
        )
        
        # Categorize orders
        debug_info = {
            "today": today.isoformat(),
            "total_orders": len(all_orders),
            "filtering_criteria": {
                "status_filter": "Orders with status in ['NEW', 'PENDING']",
                "date_filter": f"Orders with delivery_date = {today} OR delivery_date IS NULL",
                "assignment_filter": "Orders without trip.route_id OR trip.id IS NULL"
            },
            "order_categories": {
                "pending_for_assignment": [],
                "excluded_by_status": [],
                "excluded_by_date": [],
                "excluded_by_assignment": [],
                "already_assigned": [],
                "other_status": []
            },
            "specific_order_analysis": None
        }
        
        # Analyze each order
        for order in all_orders:
            # Get trip info
            trip = db.query(Trip).filter(Trip.order_id == order.id).first()
            
            order_data = {
                "order_id": order.id,
                "order_code": order.code,
                "status": order.status,
                "delivery_date": order.delivery_date.date().isoformat() if order.delivery_date else None,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "customer_address": order.customer.address if order.customer else None,
                "total": float(order.total) if order.total else 0,
                "has_trip": trip is not None,
                "trip_id": trip.id if trip else None,
                "trip_route_id": trip.route_id if trip else None,
                "trip_status": trip.status if trip else None,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
            
            # Check filtering criteria
            status_ok = order.status in ["NEW", "PENDING"]
            date_ok = order.delivery_date is None or (order.delivery_date and order.delivery_date.date() == today)
            assignment_ok = trip is None or trip.route_id is None
            
            # Categorize the order
            if status_ok and date_ok and assignment_ok:
                debug_info["order_categories"]["pending_for_assignment"].append(order_data)
            elif not status_ok:
                debug_info["order_categories"]["excluded_by_status"].append(order_data)
            elif not date_ok:
                debug_info["order_categories"]["excluded_by_date"].append(order_data)
            elif not assignment_ok:
                debug_info["order_categories"]["already_assigned"].append(order_data)
            else:
                debug_info["order_categories"]["other_status"].append(order_data)
        
        # Special analysis for the specific order if requested
        if order_id:
            specific_order = db.get(Order, order_id)
            if specific_order:
                specific_trip = db.query(Trip).filter(Trip.order_id == order_id).first()
                
                debug_info["specific_order_analysis"] = {
                    "order_id": specific_order.id,
                    "order_code": specific_order.code,
                    "status": specific_order.status,
                    "delivery_date": specific_order.delivery_date.date().isoformat() if specific_order.delivery_date else None,
                    "customer_name": specific_order.customer.name if specific_order.customer else "Unknown",
                    "customer_address": specific_order.customer.address if specific_order.customer else None,
                    "total": float(specific_order.total) if specific_order.total else 0,
                    "created_at": specific_order.created_at.isoformat() if specific_order.created_at else None,
                    "has_trip": specific_trip is not None,
                    "trip_details": {
                        "trip_id": specific_trip.id if specific_trip else None,
                        "driver_id": specific_trip.driver_id if specific_trip else None,
                        "route_id": specific_trip.route_id if specific_trip else None,
                        "status": specific_trip.status if specific_trip else None,
                        "created_at": specific_trip.created_at.isoformat() if specific_trip else None
                    } if specific_trip else None,
                    "filtering_results": {
                        "status_check": {
                            "passes": specific_order.status in ["NEW", "PENDING"],
                            "current_value": specific_order.status,
                            "required_values": ["NEW", "PENDING"]
                        },
                        "date_check": {
                            "passes": specific_order.delivery_date is None or (specific_order.delivery_date and specific_order.delivery_date.date() == today),
                            "current_value": specific_order.delivery_date.date().isoformat() if specific_order.delivery_date else None,
                            "required_value": f"{today} OR NULL"
                        },
                        "assignment_check": {
                            "passes": specific_trip is None or specific_trip.route_id is None,
                            "current_trip_id": specific_trip.id if specific_trip else None,
                            "current_route_id": specific_trip.route_id if specific_trip else None,
                            "required": "trip.id IS NULL OR trip.route_id IS NULL"
                        }
                    },
                    "eligible_for_assignment": (
                        specific_order.status in ["NEW", "PENDING"] and
                        (specific_order.delivery_date is None or (specific_order.delivery_date and specific_order.delivery_date.date() == today)) and
                        (specific_trip is None or specific_trip.route_id is None)
                    )
                }
            else:
                debug_info["specific_order_analysis"] = {"error": f"Order {order_id} not found"}
        
        # Add summary counts
        debug_info["summary"] = {
            "pending_for_assignment": len(debug_info["order_categories"]["pending_for_assignment"]),
            "excluded_by_status": len(debug_info["order_categories"]["excluded_by_status"]),
            "excluded_by_date": len(debug_info["order_categories"]["excluded_by_date"]),
            "excluded_by_assignment": len(debug_info["order_categories"]["excluded_by_assignment"]),
            "already_assigned": len(debug_info["order_categories"]["already_assigned"]),
            "other_status": len(debug_info["order_categories"]["other_status"])
        }
        
        return debug_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to debug pending orders: {str(e)}"
        )