"""Clean, simple assignment service - no over-engineering"""

import os
import json
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.order import Order
from app.models.driver import Driver
from app.models.trip import Trip
from app.models.driver_route import DriverRoute
from app.models.driver_shift import DriverShift
from app.models.driver_schedule import DriverSchedule

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - using simple distance assignment")


class AssignmentService:
    """Clean assignment service - does exactly what it says"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_client = None
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = OpenAI(api_key=openai_api_key)

    def auto_assign_all(self) -> Dict[str, Any]:
        """Auto-assign all eligible orders to drivers"""
        logger.info("Starting auto-assignment")
        
        # Get orders to assign
        orders = self._get_orders_to_assign()
        if not orders:
            return {
                "success": True,
                "message": "No orders to assign",
                "assigned": [],
                "total": 0
            }
        
        # Get available drivers
        drivers = self._get_available_drivers()
        if not drivers:
            return {
                "success": False,
                "message": "No available drivers",
                "assigned": [],
                "total": 0
            }
        
        # Get assignments from OpenAI or simple logic
        assignments = self._get_assignments(orders, drivers)
        
        # Apply assignments
        assigned = []
        for assignment in assignments:
            try:
                result = self._apply_assignment(assignment["order_id"], assignment["driver_id"])
                assigned.append(result)
            except Exception as e:
                logger.error(f"Failed to assign order {assignment['order_id']}: {e}")
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Assigned {len(assigned)} orders",
            "assigned": assigned,
            "total": len(assigned)
        }
    
    def _get_orders_to_assign(self) -> List[Dict[str, Any]]:
        """Get orders that need assignment"""
        today = date.today()
        
        orders = (
            self.db.query(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .filter(
                and_(
                    # Delivery today, before today, or no specific date
                    or_(
                        Order.delivery_date <= today,
                        Order.delivery_date.is_(None)
                    ),
                    # No trip or trip not assigned to route
                    or_(Trip.id.is_(None), Trip.route_id.is_(None))
                )
            )
            .all()
        )
        
        result = []
        for order in orders:
            result.append({
                "order_id": order.id,
                "order_code": order.code,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "address": order.customer.address if order.customer else "No address",
                "total": float(order.total) if order.total else 0,
                "lat": 3.1390,  # KL center - replace with proper geocoding later
                "lng": 101.6869
            })
        
        logger.info(f"Found {len(result)} orders to assign")
        return result
    
    def _get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get ONLY scheduled drivers - NO schedule = NO assignment"""
        today = date.today()
        
        # Get scheduled drivers for today ONLY
        scheduled_drivers = (
            self.db.query(DriverSchedule)
            .filter(
                and_(
                    DriverSchedule.schedule_date == today,
                    DriverSchedule.is_scheduled == True
                )
            )
            .all()
        )
        
        if not scheduled_drivers:
            logger.info("No scheduled drivers for today")
            return []
        
        scheduled_ids = {schedule.driver_id for schedule in scheduled_drivers}
        
        # Get clocked-in drivers
        clocked_in_shifts = self.db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        clocked_in_ids = {shift.driver_id for shift in clocked_in_shifts}
        
        # Get active drivers who are scheduled
        drivers = (
            self.db.query(Driver)
            .filter(
                and_(
                    Driver.is_active == True,
                    Driver.id.in_(scheduled_ids)
                )
            )
            .all()
        )
        
        result = []
        for driver in drivers:
            is_clocked_in = driver.id in clocked_in_ids
            
            # Count active trips
            active_trips = (
                self.db.query(Trip)
                .filter(
                    and_(
                        Trip.driver_id == driver.id,
                        Trip.status.in_(["ASSIGNED", "STARTED"])
                    )
                )
                .count()
            )
            
            # Skip if too busy
            if active_trips >= 5:
                continue
            
            # Priority: 1=Scheduled+Clocked, 2=Scheduled only
            priority = 1 if is_clocked_in else 2
            
            result.append({
                "driver_id": driver.id,
                "driver_name": driver.name or f"Driver {driver.id}",
                "is_clocked_in": is_clocked_in,
                "is_scheduled": True,  # All are scheduled
                "priority": priority,
                "active_trips": active_trips,
                "lat": 3.1390,  # KL center - replace with actual location later
                "lng": 101.6869
            })
        
        # Sort: Scheduled+Clocked first (priority 1), then Scheduled only (priority 2), then by workload
        result.sort(key=lambda d: (d["priority"], d["active_trips"]))
        
        logger.info(f"Found {len(result)} scheduled drivers (clocked+scheduled: {sum(1 for d in result if d['is_clocked_in'])}, scheduled only: {sum(1 for d in result if not d['is_clocked_in'])})")
        return result
    
    def _get_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Get optimal assignments using OpenAI or simple logic"""
        
        if self.openai_client and len(orders) > 0 and len(drivers) > 0:
            try:
                return self._openai_assignments(orders, drivers)
            except Exception as e:
                logger.error(f"OpenAI assignment failed: {e}, falling back to simple assignment")
        
        return self._simple_assignments(orders, drivers)
    
    def _openai_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Use OpenAI for optimal assignments"""
        
        prompt = f"Assign {len(orders)} delivery orders to {len(drivers)} drivers in Kuala Lumpur to minimize travel time.\n\n"
        
        prompt += "DRIVERS:\n"
        for d in drivers:
            status = "CLOCKED IN" if d["is_clocked_in"] else "SCHEDULED"
            prompt += f"- Driver {d['driver_id']}: {d['driver_name']} ({status}, {d['active_trips']} active)\n"
        
        prompt += "\nORDERS:\n"
        for o in orders:
            prompt += f"- Order {o['order_id']}: {o['customer_name']} at {o['address']} (RM{o['total']})\n"
        
        prompt += """\n\nRules:
1. Prioritize clocked-in drivers
2. Minimize total travel distance
3. Balance workload across drivers

Return only JSON:
{"assignments": [{"order_id": 123, "driver_id": 456}]}"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You optimize delivery assignments for minimum travel time."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )

        ai_response = response.choices[0].message.content
        
        # Parse JSON response
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                parsed = json.loads(ai_response[json_start:json_end])
                assignments = parsed.get("assignments", [])
                logger.info(f"OpenAI suggested {len(assignments)} assignments")
                return assignments
        except Exception as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
        
        return self._simple_assignments(orders, drivers)
    
    def _simple_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Simple priority-based assignment - no round-robin"""
        assignments = []
        
        # Group drivers by priority (already sorted)
        priority_1_drivers = [d for d in drivers if d.get("priority") == 1]  # Scheduled + Clocked
        priority_2_drivers = [d for d in drivers if d.get("priority") == 2]  # Scheduled only
        
        all_drivers = priority_1_drivers + priority_2_drivers
        
        if not all_drivers:
            logger.warning("No scheduled drivers available for assignment")
            return []
        
        # Assign orders to drivers in priority order
        driver_workload = {d["driver_id"]: d["active_trips"] for d in all_drivers}
        
        for order in orders:
            # Find driver with lowest workload in priority order
            best_driver = min(all_drivers, key=lambda d: (d["priority"], driver_workload[d["driver_id"]]))
            
            assignments.append({
                "order_id": order["order_id"],
                "driver_id": best_driver["driver_id"]
            })
            
            # Update workload for next assignment
            driver_workload[best_driver["driver_id"]] += 1
        
        logger.info(f"Priority assignment created {len(assignments)} assignments")
        return assignments
    
    def _apply_assignment(self, order_id: int, driver_id: int) -> Dict[str, Any]:
        """Apply a single assignment - create trip and route if needed"""
        order = self.db.get(Order, order_id)
        driver = self.db.get(Driver, driver_id)
        
        if not order or not driver:
            raise ValueError(f"Order {order_id} or Driver {driver_id} not found")
        
        # Get or create today's route for driver
        today = date.today()
        route = (
            self.db.query(DriverRoute)
            .filter(
                and_(
                    DriverRoute.driver_id == driver_id,
                    DriverRoute.route_date == today
                )
            )
            .first()
        )
        
        if not route:
            route = DriverRoute(
                driver_id=driver_id,
                route_date=today,
                name=f"{driver.name or 'Driver'} - {today.strftime('%b %d')}",
                notes=f"Auto-created for {driver.name or f'Driver {driver_id}'}"
            )
            self.db.add(route)
            self.db.flush()
        
        # Create or update trip
        trip = self.db.query(Trip).filter(Trip.order_id == order_id).first()
        if trip:
            if trip.status in {"DELIVERED", "SUCCESS"}:
                raise ValueError(f"Order {order_id} already delivered")
            trip.driver_id = driver_id
            trip.route_id = route.id
            trip.status = "ASSIGNED"
        else:
            trip = Trip(
                order_id=order_id,
                driver_id=driver_id,
                route_id=route.id,
                status="ASSIGNED"
            )
            self.db.add(trip)
        
        return {
            "order_id": order_id,
            "order_code": order.code,
            "driver_id": driver_id,
            "driver_name": driver.name,
            "route_id": route.id
        }