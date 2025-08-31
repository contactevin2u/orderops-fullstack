"""SMART assignment service - OpenAI + Geography, minus the over-engineering"""

import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import Order
from app.models.driver import Driver  
from app.models.trip import Trip
from app.models.driver_shift import DriverShift
from app.utils.geofencing import haversine_distance
from app.config.clock_config import HOME_BASE_LAT, HOME_BASE_LNG

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - falling back to distance-only assignment")


class SmartAssignmentService:
    """Clean service with OpenAI + geography, no over-engineering"""
    
    def __init__(self, db: Session, openai_api_key: Optional[str] = None):
        self.db = db
        self.openai_client = OpenAI(api_key=openai_api_key) if (openai_api_key and OPENAI_AVAILABLE) else None

    def get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get all active drivers with location info"""
        drivers = self.db.query(Driver).filter(Driver.is_active == True).all()
        
        # Get shift locations for clocked-in drivers
        active_shifts = self.db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        shift_locations = {shift.driver_id: shift for shift in active_shifts}
        
        result = []
        for driver in drivers:
            shift = shift_locations.get(driver.id)
            is_clocked_in = shift is not None
            
            # Count active trips
            active_trips = self.db.query(Trip).filter(
                and_(
                    Trip.driver_id == driver.id,
                    Trip.status.in_(["ASSIGNED", "STARTED"])
                )
            ).count()
            
            # Use actual location if clocked in, otherwise home base
            if is_clocked_in:
                lat, lng = shift.clock_in_lat, shift.clock_in_lng
                location = shift.clock_in_location_name or "Unknown location"
            else:
                lat, lng = HOME_BASE_LAT, HOME_BASE_LNG
                location = "Home base"
            
            result.append({
                "driver_id": driver.id,
                "driver_name": driver.name or "Unknown",
                "phone": driver.phone,
                "is_clocked_in": is_clocked_in,
                "active_trips": active_trips,
                "lat": lat,
                "lng": lng,
                "location": location,
                "available": active_trips < 3
            })
        
        # Sort: clocked-in first, then by workload
        result.sort(key=lambda d: (not d["is_clocked_in"], d["active_trips"]))
        return result

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get orders that are ready for assignment with estimated coordinates"""
        from sqlalchemy.orm import joinedload
        from datetime import date
        
        today = date.today()
        
        # Get orders that are:
        # 1. For today delivery (or no specific date)
        # 2. Not already assigned to a route (only care about trip status, not order status)
        orders = (
            self.db.query(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .filter(
                and_(
                    # Today deliveries (or no specific date)
                    or_(
                        Order.delivery_date == today,
                        Order.delivery_date.is_(None)
                    ),
                    # Not already assigned to a route (only care about trip status)
                    or_(Trip.id.is_(None), Trip.route_id.is_(None))
                )
            )
            .all()
        )
        
        result = []
        for order in orders:
            address = order.customer.address if order.customer else None
            lat, lng = self._estimate_coordinates(address)
            
            result.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "address": address or "No address",
                "lat": lat,
                "lng": lng,
                "total": float(order.total) if order.total else 0
            })
        
        return result

    def suggest_assignments(self) -> Dict[str, Any]:
        """Smart assignment using OpenAI for distance optimization"""
        drivers = [d for d in self.get_available_drivers() if d["available"]]
        orders = self.get_pending_orders()
        
        if not drivers:
            return {
                "suggestions": [],
                "method": "no_drivers",
                "available_drivers_count": 0,
                "pending_orders_count": len(orders),
                "ai_reasoning": "No available drivers"
            }
        
        if not orders:
            return {
                "suggestions": [],
                "method": "no_orders",
                "available_drivers_count": len(drivers),
                "pending_orders_count": 0,
                "ai_reasoning": "No pending orders"
            }
        
        # Try OpenAI first, fallback to distance-based
        if self.openai_client:
            try:
                return self._openai_assignments(drivers, orders)
            except Exception as e:
                logger.error(f"OpenAI failed: {e}, using distance fallback")
        
        return self._distance_assignments(drivers, orders)

    def _openai_assignments(self, drivers: List[Dict], orders: List[Dict]) -> Dict[str, Any]:
        """Use OpenAI for optimal distance-based assignments"""
        
        # Build simple, focused prompt
        prompt = f"Optimize delivery assignments to minimize fuel costs in Kuala Lumpur.\n\n"
        
        prompt += f"DRIVERS ({len(drivers)}):\n"
        for d in drivers:
            status = "CLOCKED IN" if d["is_clocked_in"] else "Available"
            prompt += f"- Driver {d['driver_id']}: {d['driver_name']} at {d['location']} ({d['lat']}, {d['lng']}) - {status}, {d['active_trips']} active trips\n"
        
        prompt += f"\nORDERS ({len(orders)}):\n"  
        for o in orders:
            prompt += f"- Order {o['order_id']}: {o['customer_name']} at {o['address']} ({o['lat']}, {o['lng']}) - RM{o['total']}\n"
        
        prompt += """
GOAL: Assign orders to minimize total travel distance (fuel costs). Prefer clocked-in drivers when distance is similar.

Return JSON only:
{
  "assignments": [
    {"order_id": 123, "driver_id": 456, "reason": "shortest distance"}
  ]
}"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper model for simple optimization
            messages=[
                {"role": "system", "content": "You are a logistics optimizer focused on minimizing fuel costs through optimal distance-based assignments."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.1
        )

        ai_response = response.choices[0].message.content
        suggestions = self._parse_ai_response(ai_response, drivers, orders)
        
        return {
            "suggestions": suggestions,
            "method": "openai_optimized",
            "available_drivers_count": len(drivers),
            "pending_orders_count": len(orders),
            "ai_reasoning": f"OpenAI optimized {len(suggestions)} assignments for minimum fuel cost"
        }

    def _distance_assignments(self, drivers: List[Dict], orders: List[Dict]) -> Dict[str, Any]:
        """Fallback: Simple distance-based assignments"""
        suggestions = []
        used_drivers = set()
        
        for order in orders:
            best_driver = None
            min_distance = float('inf')
            
            for driver in drivers:
                if driver["driver_id"] in used_drivers and len(drivers) > len(used_drivers):
                    continue  # Skip if other drivers available
                
                distance = haversine_distance(
                    driver["lat"], driver["lng"],
                    order["lat"], order["lng"]
                )
                
                # Prefer clocked-in drivers for similar distances (within 3km)
                is_better = (
                    best_driver is None or
                    distance < min_distance or
                    (driver["is_clocked_in"] and not best_driver["is_clocked_in"] and distance < min_distance + 3)
                )
                
                if is_better:
                    min_distance = distance
                    best_driver = driver
            
            if best_driver:
                suggestions.append({
                    "order_id": order["order_id"],
                    "driver_id": best_driver["driver_id"],
                    "driver_name": best_driver["driver_name"],
                    "distance_km": round(min_distance, 1),
                    "reasoning": f"Closest driver ({min_distance:.1f}km)"
                })
                used_drivers.add(best_driver["driver_id"])
        
        return {
            "suggestions": suggestions,
            "method": "distance_optimized",
            "available_drivers_count": len(drivers),
            "pending_orders_count": len(orders),
            "ai_reasoning": f"Distance-based assignment, total fuel distance minimized"
        }

    def _parse_ai_response(self, ai_response: str, drivers: List[Dict], orders: List[Dict]) -> List[Dict]:
        """Parse OpenAI JSON response"""
        try:
            # Extract JSON
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                return []
            
            parsed = json.loads(ai_response[json_start:json_end])
            suggestions = []
            
            for assignment in parsed.get("assignments", []):
                order_id = assignment.get("order_id")
                driver_id = assignment.get("driver_id")
                
                driver = next((d for d in drivers if d["driver_id"] == driver_id), None)
                order = next((o for o in orders if o["order_id"] == order_id), None)
                
                if driver and order:
                    distance = haversine_distance(
                        driver["lat"], driver["lng"],
                        order["lat"], order["lng"]
                    )
                    
                    suggestions.append({
                        "order_id": order_id,
                        "driver_id": driver_id,
                        "driver_name": driver["driver_name"],
                        "distance_km": round(distance, 1),
                        "reasoning": assignment.get("reason", "AI optimized")
                    })
            
            return suggestions
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return []

    def _estimate_coordinates(self, address: Optional[str]) -> tuple[float, float]:
        """Estimate coordinates from address (placeholder for geocoding)"""
        if not address:
            return HOME_BASE_LAT, HOME_BASE_LNG
        
        # TODO: Integrate with actual geocoding service (Google Maps, etc.)
        # For now, use home base + small random offset based on address hash
        address_hash = abs(hash(address)) % 1000
        lat_offset = (address_hash % 100) / 10000  # Small offset
        lng_offset = ((address_hash // 100) % 100) / 10000
        
        return HOME_BASE_LAT + lat_offset, HOME_BASE_LNG + lng_offset