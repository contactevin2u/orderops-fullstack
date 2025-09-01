"""Clean, simple assignment endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.firebase import get_current_admin_user
from app.db import get_session
from app.models.user import User
from app.services.assignment_service import AssignmentService
from app.utils.responses import envelope

router = APIRouter(prefix="/assignment", tags=["assignment"])


@router.post("/auto-assign")
def auto_assign_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Auto-assign all eligible orders to drivers"""
    try:
        service = AssignmentService(db)
        result = service.auto_assign_all()
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assignment failed: {str(e)}"
        )


@router.get("/status")
def get_assignment_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get current assignment status using EXACT same logic as GET /orders?unassigned=true&date=today"""
    try:
        from datetime import date, datetime
        from sqlalchemy import and_, or_, select
        from ..models.order import Order
        from ..models.trip import Trip
        from ..models.customer import Customer
        from ..utils.time import kl_day_bounds
        
        # Use EXACT same query as orders.py with unassigned=true&date=today
        today = date.today()
        start_utc, end_utc = kl_day_bounds(today)
        
        # Copy EXACT query structure from orders.py
        stmt = (
            select(Order, Customer.name.label("customer_name"), Trip)
            .join(Customer, Customer.id == Order.customer_id)
            .join(Trip, Trip.order_id == Order.id, isouter=True)
        )
        
        # Date filtering with backlog mode (same as orders.py line 128-143)
        # When unassigned=True, backlog_mode is True
        backlog_mode = True  # This is True when unassigned=True
        
        if backlog_mode:
            # Same as orders.py line 131-136: include orders with no date OR before end of today
            stmt = stmt.where(
                or_(
                    Order.delivery_date.is_(None),
                    Order.delivery_date < end_utc,
                )
            )
        
        # Unassigned filter (same as orders.py line 147)
        stmt = stmt.where(and_(or_(Trip.id.is_(None), Trip.route_id.is_(None))))
        
        # Execute query
        rows = db.execute(stmt).all()
        
        # Get available drivers
        service = AssignmentService(db)
        drivers = service._get_available_drivers()
        
        # Convert orders to simple format
        orders_data = []
        for row in rows[:5]:  # First 5 for preview
            order, customer_name, trip = row
            orders_data.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": customer_name or "Unknown",
                "total": float(order.total) if order.total else 0,
                "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None
            })
        
        return envelope({
            "orders_to_assign": len(rows),
            "available_drivers": len(drivers),
            "orders": orders_data,
            "drivers": drivers[:5]  # First 5 for preview
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )