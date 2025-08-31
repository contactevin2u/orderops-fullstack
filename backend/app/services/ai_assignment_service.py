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
from app.services.driver_schedule_service import DriverScheduleService

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
        self.schedule_service = DriverScheduleService(db)
        if openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = OpenAI(api_key=openai_api_key)
            self.ai_enabled = True
        else:
            self.openai_client = None
            self.ai_enabled = False

    def get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get all drivers currently clocked in and available for assignment"""
        active_shifts = self.db.query(DriverShift).filter(
            DriverShift.status == "ACTIVE"
        ).all()

        available_drivers = []
        for shift in active_shifts:
            driver = shift.driver
            if not driver.is_active:
                continue

            # Count current active trips
            active_trips_count = self.db.query(Trip).filter(
                and_(
                    Trip.driver_id == driver.id,
                    Trip.status.in_(["ASSIGNED", "STARTED"])
                )
            ).count()

            available_drivers.append({
                "driver_id": driver.id,
                "driver_name": driver.name,
                "phone": driver.phone,
                "shift_id": shift.id,
                "clock_in_location": shift.clock_in_location_name,
                "clock_in_lat": shift.clock_in_lat,
                "clock_in_lng": shift.clock_in_lng,
                "is_outstation": shift.is_outstation,
                "current_active_trips": active_trips_count,
                "hours_worked": (
                    datetime.now(timezone.utc) - shift.clock_in_at
                ).total_seconds() / 3600
            })

        return available_drivers

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all orders needing driver assignment (no trip or unassigned trip)"""
        from sqlalchemy import exists, or_, and_
        from app.models.trip import Trip
        
        # Find orders that either:
        # 1. Have no trip at all, OR  
        # 2. Have a trip but it's not assigned to a driver
        orders = self.db.query(Order).filter(
            or_(
                # Orders without any trip
                ~exists().where(Trip.order_id == Order.id),
                # Orders with unassigned trips
                exists().where(
                    and_(
                        Trip.order_id == Order.id,
                        or_(
                            Trip.driver_id.is_(None),
                            Trip.status.in_(["CREATED", "UNASSIGNED"])
                        )
                    )
                )
            )
        ).filter(
            # Only include orders that are in assignable state
            Order.status.in_(["NEW", "PENDING"])
        ).all()

        pending_orders = []
        for order in orders:
            # Calculate approximate coordinates from address if available
            order_lat, order_lng = self._estimate_coordinates_from_address(order.delivery_address)
            
            pending_orders.append({
                "order_id": order.id,
                "customer_name": order.customer_name,
                "delivery_address": order.delivery_address,
                "estimated_lat": order_lat,
                "estimated_lng": order_lng,
                "total_value": float(order.total_amount) if order.total_amount else 0,
                "priority": self._calculate_order_priority(order),
                "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None
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
        
        # Get scheduled drivers for today (much more intelligent than total drivers)
        from datetime import date
        today = date.today()
        scheduled_drivers = self.schedule_service.get_scheduled_drivers_for_date(today)
        scheduled_count = len(scheduled_drivers)
        
        # Get schedule summary for context
        schedule_summary = self.schedule_service.get_schedule_summary(today)

        if not available_drivers:
            # Build intelligent reasoning based on schedule
            if scheduled_count == 0:
                reasoning = "No drivers scheduled to work today. Check weekly roster and availability patterns."
            else:
                clocked_in_driver_ids = {d["driver_id"] for d in available_drivers}
                scheduled_but_not_clocked = [
                    d for d in scheduled_drivers 
                    if d["driver_id"] not in clocked_in_driver_ids
                ]
                
                if scheduled_but_not_clocked:
                    missing_names = [d["driver_name"] for d in scheduled_but_not_clocked[:3]]
                    reasoning = f"{scheduled_count} drivers scheduled for today ({', '.join(missing_names)}{' and others' if len(scheduled_but_not_clocked) > 3 else ''}) but none have clocked in yet."
                else:
                    reasoning = f"No drivers currently clocked in, though {scheduled_count} were scheduled for today."
            
            return {
                "suggestions": [],
                "method": "drivers_not_clocked_in",
                "available_drivers_count": 0,
                "pending_orders_count": len(pending_orders),
                "scheduled_drivers_count": scheduled_count,
                "total_drivers_count": self.db.query(Driver).filter(Driver.is_active == True).count(),
                "ai_reasoning": reasoning
            }

        if not pending_orders:
            return {
                "suggestions": [],
                "method": "no_orders",
                "available_drivers_count": len(available_drivers),
                "pending_orders_count": 0,
                "scheduled_drivers_count": scheduled_count,
                "total_drivers_count": self.db.query(Driver).filter(Driver.is_active == True).count(),
                "ai_reasoning": f"No pending orders to assign. {len(available_drivers)} of {scheduled_count} scheduled drivers are clocked in."
            }

        if self.ai_enabled:
            return self._ai_suggest_assignments(available_drivers, pending_orders, scheduled_count)
        else:
            return self._fallback_suggest_assignments(available_drivers, pending_orders, scheduled_count)

    def _ai_suggest_assignments(self, drivers: List[Dict], orders: List[Dict], scheduled_drivers_count: int) -> Dict[str, Any]:
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
                "scheduled_drivers_count": scheduled_drivers_count,
                "total_drivers_count": self.db.query(Driver).filter(Driver.is_active == True).count()
            }

        except Exception as e:
            logger.error(f"AI assignment failed: {e}")
            return self._fallback_suggest_assignments(drivers, orders, scheduled_drivers_count)

    def _fallback_suggest_assignments(self, drivers: List[Dict], orders: List[Dict], scheduled_drivers_count: int) -> Dict[str, Any]:
        """Fallback assignment logic using distance-based optimization"""
        suggestions = []
        
        # Simple distance-based assignment
        for order in orders:
            best_driver = None
            min_distance = float('inf')
            
            for driver in drivers:
                if driver["current_active_trips"] >= 3:  # Skip overloaded drivers
                    continue
                
                distance = haversine_distance(
                    driver["clock_in_lat"], driver["clock_in_lng"],
                    order["estimated_lat"], order["estimated_lng"]
                )
                
                if distance < min_distance:
                    min_distance = distance
                    best_driver = driver
            
            if best_driver:
                suggestions.append({
                    "order_id": order["order_id"],
                    "driver_id": best_driver["driver_id"],
                    "driver_name": best_driver["driver_name"],
                    "distance_km": round(min_distance, 1),
                    "confidence": "high" if min_distance < 10 else "medium",
                    "reasoning": f"Closest available driver ({min_distance:.1f}km away)"
                })

        return {
            "suggestions": suggestions,
            "method": "distance_optimized",
            "available_drivers_count": len(drivers),
            "pending_orders_count": len(orders),
            "scheduled_drivers_count": scheduled_drivers_count,
            "total_drivers_count": self.db.query(Driver).filter(Driver.is_active == True).count()
        }

    def _build_assignment_prompt(self, drivers: List[Dict], orders: List[Dict]) -> str:
        """Build prompt for AI assignment"""
        prompt = f"""
TASK: Suggest optimal driver-order assignments for delivery operations in Kuala Lumpur, Malaysia.

AVAILABLE DRIVERS ({len(drivers)}):
"""
        for driver in drivers:
            prompt += f"""
- Driver {driver['driver_id']} ({driver['driver_name']})
  Location: {driver['clock_in_location']} ({driver['clock_in_lat']}, {driver['clock_in_lng']})
  Outstation: {driver['is_outstation']}
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
1. Minimize total travel distance
2. Balance workload among drivers
3. Consider driver working hours (avoid overwork)
4. Prioritize high-value or urgent orders
5. Group nearby deliveries for efficiency

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
        if order.total_amount and float(order.total_amount) > 1000:
            return "high"
        elif order.delivery_date and order.delivery_date.date() == datetime.now().date():
            return "urgent"
        else:
            return "normal"