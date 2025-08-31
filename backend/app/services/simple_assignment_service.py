"""SIMPLE assignment service - no over-engineering, just results"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.order import Order
from app.models.driver import Driver  
from app.models.trip import Trip
from app.models.driver_shift import DriverShift


class SimpleAssignmentService:
    """Clean, fast, no-BS assignment service"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get active drivers, prioritize clocked-in ones"""
        # Simple query: active drivers only
        drivers = self.db.query(Driver).filter(Driver.is_active == True).all()
        
        # Get clocked-in drivers for priority
        clocked_in_ids = {
            shift.driver_id 
            for shift in self.db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        }
        
        result = []
        for driver in drivers:
            # Count active trips to avoid overloading
            active_trips = self.db.query(Trip).filter(
                and_(
                    Trip.driver_id == driver.id,
                    Trip.status.in_(["ASSIGNED", "STARTED"])
                )
            ).count()
            
            result.append({
                "driver_id": driver.id,
                "driver_name": driver.name or "Unknown",
                "phone": driver.phone,
                "is_clocked_in": driver.id in clocked_in_ids,
                "active_trips": active_trips,
                "available": active_trips < 3  # Simple overload check
            })
        
        # Sort: clocked-in first, then by workload
        result.sort(key=lambda d: (not d["is_clocked_in"], d["active_trips"]))
        return result

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get orders needing assignment - same logic as manual assignment"""
        from sqlalchemy.orm import joinedload
        
        # Use EXACT same logic as /orders?unassigned=true
        orders = (
            self.db.query(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .filter(or_(Trip.id.is_(None), Trip.route_id.is_(None)))
            .all()
        )
        
        result = []
        for order in orders:
            result.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "address": order.customer.address if order.customer else None,
                "total": float(order.total) if order.total else 0,
                "status": order.status,
                "type": order.type
            })
        
        return result

    def suggest_assignments(self) -> Dict[str, Any]:
        """Simple assignment suggestions - round-robin with availability check"""
        drivers = self.get_available_drivers()
        orders = self.get_pending_orders()
        
        # Filter to available drivers only  
        available_drivers = [d for d in drivers if d["available"]]
        
        if not available_drivers:
            return {
                "suggestions": [],
                "method": "no_drivers",
                "available_drivers_count": 0,
                "pending_orders_count": len(orders),
                "message": "No drivers available"
            }
        
        if not orders:
            return {
                "suggestions": [],
                "method": "no_orders", 
                "available_drivers_count": len(available_drivers),
                "pending_orders_count": 0,
                "message": "No pending orders"
            }
        
        # Simple round-robin assignment
        suggestions = []
        driver_index = 0
        
        for order in orders:
            if driver_index >= len(available_drivers):
                driver_index = 0  # Reset to start
                
            driver = available_drivers[driver_index]
            
            suggestions.append({
                "order_id": order["order_id"],
                "driver_id": driver["driver_id"],
                "driver_name": driver["driver_name"],
                "reasoning": f"Available driver ({driver['active_trips']} active trips)"
            })
            
            driver_index += 1
        
        return {
            "suggestions": suggestions,
            "method": "round_robin",
            "available_drivers_count": len(available_drivers),
            "pending_orders_count": len(orders),
            "message": f"Assigned {len(suggestions)} orders to {len(available_drivers)} drivers"
        }