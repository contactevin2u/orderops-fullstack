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
from app.models.customer import Customer

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
        """Get orders that need assignment - using SAME logic as orders API"""
        from app.routers.orders import kl_day_bounds
        from sqlalchemy import select
        
        today = date.today()
        start_utc, end_utc = kl_day_bounds(today)
        
        # Use EXACT same query as orders.py with unassigned=true&date=today
        stmt = (
            select(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .where(
                and_(
                    # Exclude cancelled/buyback/returned orders and their parents
                    ~Order.status.in_(["CANCELLED", "RETURNED"]),
                    Order.type != "BUYBACK",
                    Order.parent_id.is_(None),  # Exclude child orders (adjustments)
                    
                    # Backlog mode date filtering - includes overdue orders
                    or_(
                        Order.delivery_date.is_(None),
                        Order.delivery_date < end_utc,  # Includes overdue (before today)
                    ),
                    # Unassigned filter (same as orders.py)
                    or_(Trip.id.is_(None), Trip.route_id.is_(None))
                )
            )
        )
        
        orders = self.db.execute(stmt).scalars().unique().all()
        
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
        
        logger.info(f"Found {len(result)} orders to assign (includes overdue orders, excludes cancelled/buyback/returned)")
        return result
    
    def _get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get ONLY scheduled drivers - NO schedule = NO assignment"""
        today = date.today()
        logger.info(f"Looking for drivers scheduled for: {today}")
        
        # Get scheduled drivers for today ONLY
        from datetime import datetime, timedelta
        
        # Get scheduled drivers for TODAY ONLY - no date range
        # DEBUGGING: This should only return drivers 2 and 3 for 2025-09-01
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
        
        # CRITICAL DEBUG: Log exactly what we found
        logger.info(f"DEPLOYMENT CHECK: Using exact date filtering for {today}")
        logger.info(f"DEPLOYMENT CHECK: SQL query should be: schedule_date == '{today}' AND is_scheduled = True")
        
        logger.info(f"Found {len(scheduled_drivers)} scheduled drivers for {today}")
        for schedule in scheduled_drivers:
            logger.info(f"Scheduled driver: {schedule.driver_id} for {schedule.schedule_date}")
        
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
            
            # Get active trips with locations - properly load relationships for proximity
            active_trips_query = (
                self.db.query(Trip)
                .options(
                    joinedload(Trip.order).joinedload(Order.customer)
                )
                .filter(
                    and_(
                        Trip.driver_id == driver.id,
                        Trip.status.in_(["ASSIGNED", "STARTED"])
                    )
                )
                .all()
            )
            
            active_trips_count = len(active_trips_query)
            
            # Get existing trip locations for FANCY proximity consideration! 🚀
            existing_trip_locations = []
            for trip in active_trips_query:
                if trip.order and trip.order.customer and trip.order.customer.address:
                    existing_trip_locations.append({
                        "order_id": trip.order_id,
                        "address": trip.order.customer.address,
                        "status": trip.status
                    })
            
            # Priority: 1=Scheduled+Clocked, 2=Scheduled only
            priority = 1 if is_clocked_in else 2
            
            result.append({
                "driver_id": driver.id,
                "driver_name": driver.name or f"Driver {driver.id}",
                "is_clocked_in": is_clocked_in,
                "is_scheduled": True,  # All are scheduled
                "priority": priority,
                "active_trips": active_trips_count,
                "existing_trip_locations": existing_trip_locations,
                "lat": 3.1390,  # KL center - not used for location tracking
                "lng": 101.6869
            })
        
        # Sort: Scheduled+Clocked first (priority 1), then Scheduled only (priority 2), then by workload
        result.sort(key=lambda d: (d["priority"], d["active_trips"]))
        
        # CRITICAL DEBUG: Show exactly what we're returning
        logger.info(f"DEPLOYMENT CHECK: Final result has {len(result)} drivers")
        for driver in result:
            logger.info(f"DEPLOYMENT CHECK: Driver {driver['driver_id']} ({driver['driver_name']}) - Priority: {driver['priority']}")
        
        logger.info(f"Found {len(result)} scheduled drivers (clocked+scheduled: {sum(1 for d in result if d['is_clocked_in'])}, scheduled only: {sum(1 for d in result if not d['is_clocked_in'])})")
        return result
    
    def _get_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Get optimal assignments using ONLY OpenAI - no fallback"""
        
        if not self.openai_client:
            raise ValueError("OpenAI client not configured - OPENAI_API_KEY required for AI-only assignment")
        
        if len(orders) == 0 or len(drivers) == 0:
            return []
            
        # AI-ONLY assignment - no fallback allowed
        return self._openai_assignments(orders, drivers)
    
    def _openai_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Use OpenAI for optimal assignments with proximity consideration"""
        
        prompt = f"""DELIVERY ASSIGNMENT OPTIMIZATION
Assign {len(orders)} new delivery orders to {len(drivers)} drivers in Kuala Lumpur/Selangor for optimal routing.

DRIVERS WITH CURRENT ASSIGNMENTS:"""
        
        for d in drivers:
            status = "CLOCKED IN" if d["is_clocked_in"] else "SCHEDULED"
            prompt += f"\n- Driver {d['driver_id']}: {d['driver_name']} ({status})"
            
            existing_locations = d.get('existing_trip_locations', [])
            if existing_locations:
                prompt += f" | Current assignments ({len(existing_locations)}):"
                for loc in existing_locations[:3]:  # Limit to 3 for brevity
                    prompt += f"\n  • Order {loc['order_id']}: {loc['address'][:50]}{'...' if len(loc['address']) > 50 else ''}"
                if len(existing_locations) > 3:
                    prompt += f"\n  • ... and {len(existing_locations) - 3} more"
            else:
                prompt += " | No current assignments"
        
        prompt += f"\n\nNEW ORDERS TO ASSIGN:"
        for o in orders:
            prompt += f"\n- Order {o['order_id']}: {o['customer_name']} at {o['address']} (RM{o['total']:.0f})"
        
        prompt += f"""\n\nOPTIMIZATION RULES:
1. PRIORITY: Clocked-in drivers > Scheduled drivers
2. PROXIMITY: Assign orders near driver's existing assignments to minimize travel
3. WORKLOAD: Balance total assignments across drivers
4. EFFICIENCY: Group nearby deliveries to same driver when possible

Return optimized assignments as JSON schema:
{{"assignments": [{{"order_id": int, "driver_id": int, "reason": "proximity/workload/priority"}}]}}

Focus on geographic efficiency - drivers with existing assignments in an area should get nearby new orders."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a logistics optimization AI specializing in Malaysian delivery routing. 
                    You understand Malaysian geography, major roads, and traffic patterns in Kuala Lumpur/Selangor region.
                    
                    Your goal: Minimize total driver travel time and distance by intelligently clustering nearby deliveries.
                    Consider existing driver assignments to create efficient route continuity.
                    
                    Always return valid JSON only - no explanations or markdown formatting."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1,
            response_format={"type": "json_object"}
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
        """Enhanced assignment with proximity consideration"""
        assignments = []
        
        # Group drivers by priority (already sorted)
        priority_1_drivers = [d for d in drivers if d.get("priority") == 1]  # Scheduled + Clocked
        priority_2_drivers = [d for d in drivers if d.get("priority") == 2]  # Scheduled only
        
        all_drivers = priority_1_drivers + priority_2_drivers
        
        if not all_drivers:
            logger.warning("No scheduled drivers available for assignment")
            return []
        
        # Track workload
        driver_workload = {d["driver_id"]: d["active_trips"] for d in all_drivers}
        
        for order in orders:
            best_driver = None
            best_score = float('inf')
            
            # Evaluate each driver for this order
            for driver in all_drivers:
                # Base score from priority and workload
                priority_score = driver["priority"] * 1000  # High penalty for lower priority
                workload_score = driver_workload[driver["driver_id"]] * 100
                
                # Proximity bonus: check if order is near existing assignments
                proximity_bonus = 0
                existing_locations = driver.get('existing_trip_locations', [])
                if existing_locations:
                    order_address = order.get('address', '').lower()
                    for existing_loc in existing_locations:
                        existing_address = existing_loc.get('address', '').lower()
                        
                        # Simple geographic proximity heuristics for Malaysia
                        if self._addresses_likely_nearby(order_address, existing_address):
                            proximity_bonus = -500  # Strong bonus for proximity
                            break
                        elif self._addresses_same_area(order_address, existing_address):
                            proximity_bonus = -200  # Moderate bonus for same general area
                
                # Calculate final score (lower is better)
                total_score = priority_score + workload_score + proximity_bonus
                
                if total_score < best_score:
                    best_score = total_score
                    best_driver = driver
            
            if best_driver:
                assignments.append({
                    "order_id": order["order_id"],
                    "driver_id": best_driver["driver_id"]
                })
                
                # Update workload for next assignment
                driver_workload[best_driver["driver_id"]] += 1
        
        logger.info(f"Enhanced proximity assignment created {len(assignments)} assignments")
        return assignments
    
    def _addresses_likely_nearby(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are likely nearby (same street/building/area)"""
        # Extract common Malaysian address patterns
        addr1_parts = set(addr1.split())
        addr2_parts = set(addr2.split())
        
        # Check for exact street name matches
        common_words = addr1_parts.intersection(addr2_parts)
        
        # Common indicators of nearby addresses
        nearby_indicators = {
            'jalan', 'jln', 'lorong', 'taman', 'bandar', 'pju', 'ss', 'usj', 
            'section', 'seksyen', 'lot', 'no', 'blok', 'block', 'plaza', 'mall'
        }
        
        # If they share specific location identifiers
        location_matches = len(common_words.intersection(nearby_indicators))
        word_overlap = len(common_words) / max(len(addr1_parts), len(addr2_parts), 1)
        
        return location_matches >= 2 or word_overlap > 0.4
    
    def _addresses_same_area(self, addr1: str, addr2: str) -> bool:
        """Check if addresses are in same general area"""
        addr1_parts = set(addr1.split())
        addr2_parts = set(addr2.split())
        
        # Major area identifiers
        area_indicators = {
            'kuala', 'lumpur', 'kl', 'selangor', 'shah', 'alam', 'petaling', 'jaya', 'pj',
            'subang', 'klang', 'ampang', 'cheras', 'kepong', 'wangsa', 'maju', 'setapak',
            'damansara', 'bangsar', 'mont', 'kiara', 'ttdi', 'puchong', 'seri', 'kembangan'
        }
        
        common_areas = addr1_parts.intersection(addr2_parts).intersection(area_indicators)
        return len(common_areas) > 0
    
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