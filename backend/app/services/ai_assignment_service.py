"""AI-assisted order assignment service using OpenAI API"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.order import Order
from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.trip import Trip
from app.utils.geofencing import haversine_distance
from app.config.clock_config import HOME_BASE_LAT, HOME_BASE_LNG

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available - AI assignment will be disabled")


class AIAssignmentService:
    def __init__(self, db: Session, openai_api_key: Optional[str] = None):
        self.db = db
        if openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = OpenAI(api_key=openai_api_key)
            self.ai_enabled = True
        else:
            self.openai_client = None
            self.ai_enabled = False

    def get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get scheduled drivers with priority for clocked-in drivers"""
        from datetime import date
        
        # Get drivers scheduled for today - use same logic as driver-schedule page
        today = date.today()
        from ..models.driver import Driver
        
        # First get all active drivers
        all_drivers = self.db.query(Driver).filter(Driver.is_active == True).limit(1000).all()
        
        # Get scheduled drivers (with fallback)
        scheduled_driver_ids = set()
        try:
            from ..services.driver_schedule_service import DriverScheduleService
            schedule_service = DriverScheduleService(self.db)
            scheduled_drivers = schedule_service.get_scheduled_drivers_for_date(today)
            scheduled_driver_ids = {d["driver_id"] for d in scheduled_drivers}
        except Exception as e:
            logger.warning(f"Schedule service failed, using fallback: {e}")
            # Fallback: if scheduling fails, all active drivers are available
            scheduled_driver_ids = {d.id for d in all_drivers}
        
        # Filter to only scheduled drivers
        available_drivers = []
        drivers = [d for d in all_drivers if d.id in scheduled_driver_ids]
        
        # Get current active shifts for priority
        active_shifts = self.db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        active_shifts_dict = {shift.driver_id: shift for shift in active_shifts}
        
        for driver in drivers:
            active_shift = active_shifts_dict.get(driver.id)
            is_clocked_in = active_shift is not None
            
            # Count current active trips
            active_trips_count = self.db.query(Trip).filter(
                and_(
                    Trip.driver_id == driver.id,
                    Trip.status.in_(["ASSIGNED", "STARTED"])
                )
            ).count()
            
            driver_data = {
                "driver_id": driver.id,
                "driver_name": driver.name or "Unknown Driver",
                "phone": driver.phone,
                "is_clocked_in": is_clocked_in,
                "current_active_trips": active_trips_count,
                "priority": "high" if is_clocked_in else "normal"  # Clocked-in scheduled drivers get priority
            }
            
            if is_clocked_in:
                # Use actual shift location for clocked-in drivers
                driver_data.update({
                    "shift_id": active_shift.id,
                    "clock_in_location": active_shift.clock_in_location_name,
                    "clock_in_lat": active_shift.clock_in_lat,
                    "clock_in_lng": active_shift.clock_in_lng,
                    "is_outstation": active_shift.is_outstation,
                    "hours_worked": (
                        datetime.now(timezone.utc) - active_shift.clock_in_at
                    ).total_seconds() / 3600
                })
            else:
                # Use home base for scheduled but not clocked-in drivers
                driver_data.update({
                    "shift_id": None,
                    "clock_in_location": "Home Base (Scheduled)",
                    "clock_in_lat": HOME_BASE_LAT,
                    "clock_in_lng": HOME_BASE_LNG,
                    "is_outstation": False,
                    "hours_worked": 0.0
                })
            
            available_drivers.append(driver_data)

        # Sort by priority: clocked-in scheduled drivers first, then by active trips
        available_drivers.sort(key=lambda d: (d["priority"] != "high", d["current_active_trips"]))
        
        return available_drivers

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all orders needing driver assignment (no trip or unassigned trip)"""
        from sqlalchemy import exists, or_, and_
        from app.models.trip import Trip
        
        # Use the SAME logic as the working manual assignment endpoint (/orders?unassigned=true)
        # This matches orders.py line 147: Trip.id.is_(None) OR Trip.route_id.is_(None)
        from sqlalchemy.orm import joinedload
        from sqlalchemy import select
        
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))  # Eagerly load customer
            .join(Trip, Trip.order_id == Order.id, isouter=True)  # LEFT JOIN trips
            .filter(
                # Same logic as manual assignment: no trip OR no route assigned  
                and_(
                    or_(Trip.id.is_(None), Trip.route_id.is_(None))
                )
            )
        )
        
        orders = self.db.execute(stmt).scalars().unique().all()

        pending_orders = []
        for order in orders:
            # Get customer information through relationship
            customer_name = order.customer.name if order.customer else "Unknown Customer"
            delivery_address = order.customer.address if order.customer else None
            
            # Calculate approximate coordinates from address if available
            order_lat, order_lng = self._estimate_coordinates_from_address(delivery_address)
            
            pending_orders.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": customer_name,
                "delivery_address": delivery_address or "No address provided",
                "estimated_lat": order_lat,
                "estimated_lng": order_lng,
                "total_value": float(order.total) if order.total else 0,  # Use 'total' field
                "priority": self._calculate_order_priority(order),
                "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
                "order_type": order.type,
                "order_status": order.status
            })

        return pending_orders

    def suggest_assignments(self) -> Dict[str, Any]:
        """
        Use AI to suggest optimal driver-order assignments
        
        Returns:
            Dictionary with assignment suggestions and reasoning
        """
        available_drivers = self.get_available_drivers()
        pending_orders = self.get_pending_orders()
        
        # Count available drivers (simple logic)
        available_count = len(available_drivers)

        if not available_drivers:
            total_active_drivers = self.db.query(Driver).filter(Driver.is_active == True).count()
            
            reasoning = f"No active drivers found. Database shows {total_active_drivers} active drivers total."
            
            return {
                "suggestions": [],
                "method": "no_drivers_available", 
                "available_drivers_count": 0,
                "pending_orders_count": len(pending_orders),
                "total_drivers_count": self.db.query(Driver).count(),
                "ai_reasoning": reasoning
            }

        if not pending_orders:
            return {
                "suggestions": [],
                "method": "no_orders",
                "available_drivers_count": len(available_drivers),
                "pending_orders_count": 0,
                "total_drivers_count": self.db.query(Driver).count(),
                "ai_reasoning": f"No pending orders to assign. {len(available_drivers)} active drivers available."
            }

        if self.ai_enabled:
            return self._ai_suggest_assignments(available_drivers, pending_orders, available_count)
        else:
            return self._fallback_suggest_assignments(available_drivers, pending_orders, available_count)

    def _ai_suggest_assignments(self, drivers: List[Dict], orders: List[Dict], available_drivers_count: int) -> Dict[str, Any]:
        """Use OpenAI to suggest assignments"""
        try:
            prompt = self._build_assignment_prompt(drivers, orders)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert logistics coordinator for a delivery company in Malaysia. Optimize driver-order assignments considering distance, workload, and efficiency."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3
            )

            ai_response = response.choices[0].message.content
            suggestions = self._parse_ai_response(ai_response, drivers, orders)
            
            return {
                "suggestions": suggestions,
                "ai_reasoning": ai_response,
                "method": "ai_optimized",
                "available_drivers_count": len(drivers),
                "pending_orders_count": len(orders),
                "total_drivers_count": self.db.query(Driver).filter(Driver.is_active == True).count()
            }

        except Exception as e:
            logger.error(f"AI assignment failed: {e}")
            return self._fallback_suggest_assignments(drivers, orders, scheduled_drivers_count)

    def _fallback_suggest_assignments(self, drivers: List[Dict], orders: List[Dict], scheduled_drivers_count: int) -> Dict[str, Any]:
        """Fallback assignment logic using distance-based optimization with priority for clocked-in drivers"""
        suggestions = []
        
        # Simple distance-based assignment with priority consideration
        for order in orders:
            best_driver = None
            min_distance = float('inf')
            best_priority = "normal"
            
            for driver in drivers:
                if driver["current_active_trips"] >= 3:  # Skip overloaded drivers
                    continue
                
                distance = haversine_distance(
                    driver["clock_in_lat"], driver["clock_in_lng"],
                    order["estimated_lat"], order["estimated_lng"]
                )
                
                # Priority logic: prefer clocked-in drivers for similar distances
                is_better = False
                if best_driver is None:
                    is_better = True
                elif driver["priority"] == "high" and best_priority == "normal":
                    # Clocked-in driver beats non-clocked-in driver even if slightly farther
                    is_better = distance < min_distance + 5  # 5km tolerance for priority
                elif driver["priority"] == best_priority:
                    # Same priority level, use distance
                    is_better = distance < min_distance
                
                if is_better:
                    min_distance = distance
                    best_driver = driver
                    best_priority = driver["priority"]
            
            if best_driver:
                clocked_in_status = " (clocked in)" if best_driver["is_clocked_in"] else " (not clocked in)"
                suggestions.append({
                    "order_id": order["order_id"],
                    "driver_id": best_driver["driver_id"],
                    "driver_name": best_driver["driver_name"],
                    "distance_km": round(min_distance, 1),
                    "confidence": "high" if min_distance < 10 else "medium",
                    "reasoning": f"Best available scheduled driver ({min_distance:.1f}km away{clocked_in_status})"
                })

        return {
            "suggestions": suggestions,
            "method": "priority_distance_optimized",
            "available_drivers_count": len(drivers),
            "pending_orders_count": len(orders),
            "scheduled_drivers_count": scheduled_drivers_count,
            "total_drivers_count": self.db.query(Driver).count(),
            "clocked_in_drivers": len([d for d in drivers if d["is_clocked_in"]])
        }

    def _build_assignment_prompt(self, drivers: List[Dict], orders: List[Dict]) -> str:
        """Build prompt for AI assignment"""
        prompt = f"""
TASK: Suggest optimal driver-order assignments for delivery operations in Kuala Lumpur, Malaysia.

AVAILABLE DRIVERS ({len(drivers)}):
"""
        for driver in drivers:
            clocked_in_str = "✓ Clocked In" if driver['is_clocked_in'] else "○ Not Clocked In"
            priority_str = "HIGH PRIORITY" if driver['priority'] == 'high' else "Normal"
            prompt += f"""
- Driver {driver['driver_id']} ({driver['driver_name']}) - {priority_str}
  Status: {clocked_in_str}
  Location: {driver['clock_in_location']} ({driver['clock_in_lat']}, {driver['clock_in_lng']})
  Outstation: {driver.get('is_outstation', False)}
  Active trips: {driver['current_active_trips']}
  Hours worked: {driver['hours_worked']:.1f}h
"""

        prompt += f"""

PENDING ORDERS ({len(orders)}):
"""
        for order in orders:
            prompt += f"""
- Order {order['order_id']}
  Customer: {order['customer_name']}
  Address: {order['delivery_address']}
  Value: RM{order['total_value']}
  Priority: {order['priority']}
  Estimated coords: ({order['estimated_lat']}, {order['estimated_lng']})
"""

        prompt += """

ASSIGNMENT CRITERIA:
1. **PRIORITY**: Prefer clocked-in drivers (HIGH PRIORITY) when distance is similar (within 5km)
2. Minimize total travel distance
3. Balance workload among scheduled drivers
4. Consider driver working hours (avoid overwork for clocked-in drivers)
5. Prioritize high-value or urgent orders
6. Group nearby deliveries for efficiency

NOTE: All drivers shown are scheduled for today. Clocked-in drivers get priority but non-clocked-in drivers can still receive assignments.

Provide assignments in JSON format:
{
  "assignments": [
    {
      "order_id": 123,
      "driver_id": 456,
      "reasoning": "Closest driver with low workload"
    }
  ],
  "unassigned_orders": [order_ids],
  "reasoning": "Overall strategy explanation"
}
"""
        return prompt

    def _parse_ai_response(self, ai_response: str, drivers: List[Dict], orders: List[Dict]) -> List[Dict]:
        """Parse AI response and convert to standardized format"""
        try:
            # Extract JSON from AI response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]
            
            parsed = json.loads(json_str)
            suggestions = []
            
            for assignment in parsed.get("assignments", []):
                order_id = assignment["order_id"]
                driver_id = assignment["driver_id"]
                
                # Find driver and order details
                driver = next((d for d in drivers if d["driver_id"] == driver_id), None)
                order = next((o for o in orders if o["order_id"] == order_id), None)
                
                if driver and order:
                    distance = haversine_distance(
                        driver["clock_in_lat"], driver["clock_in_lng"],
                        order["estimated_lat"], order["estimated_lng"]
                    )
                    
                    suggestions.append({
                        "order_id": order_id,
                        "driver_id": driver_id,
                        "driver_name": driver["driver_name"],
                        "distance_km": round(distance, 1),
                        "confidence": "high",
                        "reasoning": assignment.get("reasoning", "AI recommended")
                    })
            
            return suggestions
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return []

    def _estimate_coordinates_from_address(self, address: Optional[str]) -> tuple[float, float]:
        """Estimate coordinates from address - simplified for demo"""
        if not address:
            return HOME_BASE_LAT, HOME_BASE_LNG
        
        # For demo purposes, return home base coordinates
        # In production, integrate with geocoding service
        return HOME_BASE_LAT, HOME_BASE_LNG

    def _calculate_order_priority(self, order: Order) -> str:
        """Calculate order priority based on various factors"""
        # Simple priority calculation for demo
        if order.total and float(order.total) > 1000:
            return "high"
        elif order.delivery_date and order.delivery_date.date() == datetime.now().date():
            return "urgent"
        else:
            return "normal"

