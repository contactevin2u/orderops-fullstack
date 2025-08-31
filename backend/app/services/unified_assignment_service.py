"""Unified Assignment Service - Automate everything, manual edit only when needed"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import Order
from app.models.driver import Driver  
from app.models.trip import Trip
from app.models.driver_route import DriverRoute
from app.services.smart_assignment_service import SmartAssignmentService

# Shared route creation utility
def get_or_create_daily_route(db: Session, driver_id: int, route_date: date) -> Tuple[DriverRoute, bool]:
    """
    Shared utility to get or create daily route for a driver.
    Returns (route, was_created)
    """
    # Check if driver already has a route for the given date
    existing_route = (
        db.query(DriverRoute)
        .filter(
            and_(
                DriverRoute.driver_id == driver_id,
                DriverRoute.route_date == route_date
            )
        )
        .one_or_none()
    )
    
    if existing_route:
        return existing_route, False
    
    # Create new daily route
    driver = db.get(Driver, driver_id)
    route_name = f"{driver.name or 'Driver'} - {route_date.strftime('%b %d')}"
    
    new_route = DriverRoute(
        driver_id=driver_id,
        route_date=route_date,
        name=route_name,
        notes=f"Auto-created route for {driver.name or f'Driver {driver_id}'}"
    )
    
    db.add(new_route)
    db.flush()  # Get the ID
    
    logger.info(f"Created new route {new_route.id} for driver {driver_id} on {route_date}")
    return new_route, True

logger = logging.getLogger(__name__)


class UnifiedAssignmentService:
    """
    Unified workflow: Smart assignment creates routes automatically,
    manual editing only when needed
    """
    
    def __init__(self, db: Session, openai_api_key: Optional[str] = None):
        self.db = db
        self.smart_service = SmartAssignmentService(db, openai_api_key)

    def auto_assign_new_orders(self) -> Dict[str, Any]:
        """
        Main automation: Auto-assign all new orders using smart assignment
        and create routes automatically
        """
        logger.info("Starting auto-assignment of new orders")
        
        # Get smart assignment suggestions
        suggestions_result = self.smart_service.suggest_assignments()
        
        if not suggestions_result["suggestions"]:
            return {
                "success": True,
                "message": "No new orders to assign",
                "assigned_count": 0,
                "routes_created": 0,
                "details": suggestions_result
            }
        
        # Apply all suggestions and auto-create routes
        assignments = []
        routes_created = {}  # driver_id -> route
        failed = []
        
        for suggestion in suggestions_result["suggestions"]:
            try:
                result = self._apply_assignment_with_auto_route(suggestion)
                assignments.append(result["assignment"])
                
                if result["route_created"]:
                    routes_created[suggestion["driver_id"]] = result["route"]
                    
            except Exception as e:
                logger.error(f"Failed to assign order {suggestion['order_id']}: {e}")
                failed.append({
                    "order_id": suggestion["order_id"],
                    "driver_id": suggestion["driver_id"],
                    "error": str(e)
                })
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Auto-assigned {len(assignments)} orders to {len(routes_created)} routes",
            "assigned_count": len(assignments),
            "routes_created": len(routes_created),
            "assignments": assignments,
            "routes": list(routes_created.values()),
            "failed": failed,
            "method": suggestions_result["method"]
        }

    def _apply_assignment_with_auto_route(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """Apply assignment and auto-create route if needed"""
        order_id = suggestion["order_id"]
        driver_id = suggestion["driver_id"]
        today = date.today()
        
        # Get or create route using shared utility
        route, route_created = get_or_create_daily_route(self.db, driver_id, today)
        
        # Create/Update trip
        order = self.db.get(Order, order_id)
        driver = self.db.get(Driver, driver_id)
        
        if not order or not driver:
            raise ValueError(f"Order {order_id} or Driver {driver_id} not found")
        
        trip = self.db.query(Trip).filter_by(order_id=order.id).one_or_none()
        
        if trip:
            # Update existing trip
            if trip.status in {"DELIVERED", "SUCCESS"}:
                raise ValueError("Order already delivered")
            trip.driver_id = driver.id
            trip.route_id = route.id
            trip.status = "ASSIGNED"
        else:
            # Create new trip
            trip = Trip(
                order_id=order.id,
                driver_id=driver.id,
                route_id=route.id,
                status="ASSIGNED"
            )
            self.db.add(trip)
        
        # Don't change order.status - follow manual assignment pattern
        # Only the trip.status = "ASSIGNED" matters
        
        return {
            "assignment": {
                "order_id": order_id,
                "driver_id": driver_id,
                "driver_name": driver.name,
                "route_id": route.id,
                "order_code": order.code
            },
            "route_created": route_created,
            "route": {
                "id": route.id,
                "driver_id": route.driver_id,
                "driver_name": driver.name,
                "route_date": route.route_date.isoformat(),
                "name": route.name
            }
        }


    def get_on_hold_orders(self) -> List[Dict[str, Any]]:
        """Get orders that are on hold and need customer delivery date input"""
        on_hold_orders = (
            self.db.query(Order)
            .filter(Order.status == "ON_HOLD")
            .all()
        )
        
        result = []
        for order in on_hold_orders:
            result.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "customer_phone": order.customer.phone if order.customer else None,
                "address": order.customer.address if order.customer else None,
                "total": float(order.total) if order.total else 0,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "on_hold_reason": order.notes or "Customer requested delivery delay"
            })
        
        return result

    def handle_on_hold_response(self, order_id: int, customer_available: bool, delivery_date: Optional[str] = None) -> Dict[str, Any]:
        """Handle driver response to on-hold order: customer said when to deliver?"""
        order = self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if customer_available and delivery_date:
            # Customer gave a date - schedule for that date
            try:
                parsed_date = datetime.fromisoformat(delivery_date).date()
                order.delivery_date = parsed_date
                order.status = "PENDING"  # Back to pending for assignment
                order.notes = f"Customer requested delivery on {parsed_date.strftime('%B %d, %Y')}"
                
                # Just reschedule - don't trigger auto-assignment to avoid recursion
                if parsed_date == date.today():
                    message = f"Order rescheduled for today and ready for assignment"
                else:
                    message = f"Order rescheduled for {parsed_date.strftime('%B %d, %Y')}"
                
            except ValueError:
                raise ValueError("Invalid delivery date format")
        else:
            # Customer said no specific date - retry tomorrow
            from datetime import timedelta
            tomorrow = datetime.now().date() + timedelta(days=1)
            order.delivery_date = tomorrow
            order.status = "PENDING"
            order.notes = "Customer has no specific date preference, rescheduled for tomorrow"
            message = f"Order rescheduled for tomorrow ({tomorrow.strftime('%B %d, %Y')})"
        
        self.db.commit()
        
        return {
            "success": True,
            "message": message,
            "order_id": order_id,
            "new_status": order.status,
            "new_delivery_date": order.delivery_date.isoformat() if order.delivery_date else None
        }

    def get_hidden_orders(self) -> List[Dict[str, Any]]:
        """Get orders that should be hidden from assignment (returned, cancelled, etc.)"""
        hidden_statuses = ["RETURNED", "CANCELLED", "REFUNDED", "VOID"]
        
        hidden_orders = (
            self.db.query(Order)
            .filter(Order.status.in_(hidden_statuses))
            .all()
        )
        
        result = []
        for order in hidden_orders:
            result.append({
                "order_id": order.id,
                "order_code": order.code,
                "status": order.status,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "total": float(order.total) if order.total else 0,
                "hidden_reason": f"Order {order.status.lower()}"
            })
        
        return result

    def get_manual_edit_summary(self) -> Dict[str, Any]:
        """Get summary of current assignments for manual editing if needed"""
        today = date.today()
        
        # Get today's routes with their orders
        routes = (
            self.db.query(DriverRoute)
            .filter(DriverRoute.route_date == today)
            .all()
        )
        
        route_summaries = []
        for route in routes:
            # Get trips for this route
            trips = (
                self.db.query(Trip)
                .filter(Trip.route_id == route.id)
                .all()
            )
            
            orders = []
            for trip in trips:
                order = self.db.get(Order, trip.order_id)
                if order:
                    orders.append({
                        "order_id": order.id,
                        "order_code": order.code,
                        "customer_name": order.customer.name if order.customer else "Unknown",
                        "status": trip.status,
                        "total": float(order.total) if order.total else 0
                    })
            
            driver = self.db.get(Driver, route.driver_id)
            route_summaries.append({
                "route_id": route.id,
                "driver_id": route.driver_id,
                "driver_name": driver.name if driver else f"Driver {route.driver_id}",
                "route_name": route.name,
                "orders_count": len(orders),
                "orders": orders,
                "can_add_secondary_driver": route.secondary_driver_id is None
            })
        
        return {
            "date": today.isoformat(),
            "routes_count": len(route_summaries),
            "total_orders": sum(r["orders_count"] for r in route_summaries),
            "routes": route_summaries
        }