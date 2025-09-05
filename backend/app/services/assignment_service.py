"""Clean, simple assignment service - no over-engineering"""

import os
import json
import logging
from datetime import date, datetime, timezone, timedelta
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

from openai import OpenAI


class AssignmentService:
    """Clean assignment service - does exactly what it says"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_client = None
        
        from ..core.config import settings
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
        
        logger.debug(f"Found {len(result)} orders to assign")
        return result
    
    def _get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get ONLY scheduled drivers - NO schedule = NO assignment"""
        today = date.today()
        logger.info(f"Looking for drivers scheduled for: {today}")
        
        # Get scheduled drivers for today ONLY
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
        
        if not scheduled_drivers:
            logger.debug("No scheduled drivers for today")
            return []
        
        scheduled_ids = {schedule.driver_id for schedule in scheduled_drivers}
        
        # Get clocked-in drivers
        clocked_in_shifts = self.db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        clocked_in_ids = {shift.driver_id for shift in clocked_in_shifts}
        
        # OPTIMIZED: Get drivers with active trips in single query
        from sqlalchemy import func
        
        # Get active trips count per driver in one query
        active_trips_subquery = (
            self.db.query(
                Trip.driver_id,
                func.count(Trip.id).label('active_count')
            )
            .filter(Trip.status.in_(["ASSIGNED", "STARTED"]))
            .group_by(Trip.driver_id)
            .subquery()
        )
        
        # Get drivers with their active trip counts
        drivers = (
            self.db.query(Driver, active_trips_subquery.c.active_count)
            .outerjoin(active_trips_subquery, Driver.id == active_trips_subquery.c.driver_id)
            .filter(
                and_(
                    Driver.is_active == True,
                    Driver.id.in_(scheduled_ids)
                )
            )
            .all()
        )
        
        result = []
        for driver, active_count in drivers:
            is_clocked_in = driver.id in clocked_in_ids
            active_trips_count = active_count or 0
            
            # Get recent delivery history for area familiarity (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            recent_trips = (
                self.db.query(Trip)
                .options(joinedload(Trip.order).joinedload(Order.customer))
                .filter(
                    and_(
                        Trip.driver_id == driver.id,
                        Trip.status == "DELIVERED",
                        Trip.delivered_at >= thirty_days_ago
                    )
                )
                .limit(10)  # Last 10 deliveries for area pattern
                .all()
            )
            
            existing_trip_locations = []
            for trip in recent_trips:
                if trip.order and trip.order.customer and trip.order.customer.address:
                    existing_trip_locations.append({
                        "order_id": trip.order_id,
                        "address": trip.order.customer.address,
                        "status": "DELIVERED"
                    })
            
            # Priority: 1=Scheduled+Clocked, 2=Scheduled only
            priority = 1 if is_clocked_in else 2
            
            result.append({
                "driver_id": driver.id,
                "driver_name": driver.name or f"Driver {driver.id}",
                "base_warehouse": getattr(driver, 'base_warehouse', 'BATU_CAVES'),
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
        
        logger.debug(f"Found {len(result)} scheduled drivers")
        return result
    
    def _get_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Get optimal assignments using OpenAI with fallback to simple logic"""
        
        if len(orders) == 0 or len(drivers) == 0:
            return []
        
        # ONLY use OpenAI - no manual fallback logic
        if not self.openai_client:
            raise ValueError("OpenAI API key required for PhD-level route optimization. Manual assignment disabled.")
        
        return self._openai_assignments(orders, drivers)
    
    def _openai_assignments(self, orders: List[Dict], drivers: List[Dict]) -> List[Dict[str, Any]]:
        """Use OpenAI for optimal assignments with proximity consideration"""
        
        prompt = f"""DELIVERY ASSIGNMENT OPTIMIZATION
Assign {len(orders)} new delivery orders to {len(drivers)} drivers in Kuala Lumpur/Selangor for optimal routing.

DRIVERS WITH CURRENT ASSIGNMENTS:"""
        
        for d in drivers:
            status = "CLOCKED IN" if d["is_clocked_in"] else "SCHEDULED"
            warehouse = d.get('base_warehouse', 'BATU_CAVES')
            warehouse_label = "📍 Batu Caves" if warehouse == "BATU_CAVES" else "📍 Kota Kinabalu"
            prompt += f"\n- Driver {d['driver_id']}: {d['driver_name']} ({status}) - {warehouse_label}"
            
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
        
        prompt += f"""\n\nWAREHOUSE & GEOGRAPHY CONTEXT:
- MAIN BASE: Batu Caves, Selangor (Peninsular Malaysia)
- SABAH BASE: Kota Kinabalu warehouse (East Malaysia)

PENINSULAR ROUTES from Batu Caves:
- NORTH: Kedah (Alor Setar), Penang (Georgetown), Perlis - can be 1-2 drivers
- SOUTH: Johor (JB), Melaka, N9 - can be 1-2 drivers depending on spread
- EAST: Pahang (Kuantan), Terengganu, Kelantan (Kota Bharu) - SPLIT if Pahang+Kelantan
- LOCAL: KL, Selangor areas - multiple drivers

SABAH ROUTES from Kota Kinabalu:
- All Sabah orders MUST be assigned to Kota Kinabalu-based drivers only
- Sabah areas: Kota Kinabalu, Sandakan, Tawau, Lahad Datu, Kota Belud
- DO NOT assign Sabah orders to Peninsular drivers (different logistics network)

OPTIMIZATION STRATEGY:
1. ROUTE CLUSTERING: If driver has orders going NORTH (Kedah), prioritize other NORTH orders (Penang) to same driver
2. SMART SPLITTING: For EAST route, don't mix Pahang+Kelantan orders to same driver (400+ km apart)
3. FUEL EFFICIENCY: Group orders by highway routes (Plus Highway directions)
4. DRIVER PRIORITY: Clocked-in drivers > Scheduled drivers
5. WORKLOAD BALANCE: But geographic efficiency overrides pure workload balance

CRITICAL: Consider total driving distance and fuel costs. Sometimes 2 drivers for same direction is more efficient than 1 driver doing massive detours.

Return optimized assignments as JSON schema:
{{"assignments": [{{"order_id": int, "driver_id": int, "reason": "route_efficiency/fuel_savings/geographic_clustering"}}]}}"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",  # Use full GPT-4 for PhD-level optimization
            messages=[
                {
                    "role": "system", 
                    "content": """You are a PhD-level Logistics Operations Research specialist with expertise in:

🎓 ACADEMIC CREDENTIALS:
- PhD in Operations Research & Supply Chain Optimization  
- 15+ years optimizing delivery networks across Southeast Asia
- Published researcher in vehicle routing problems (VRP) and traveling salesman optimization
- Expert in Malaysian geography, road networks, traffic patterns, and logistics costs

🧠 ADVANCED OPTIMIZATION TECHNIQUES:
- Multi-depot vehicle routing problem (MD-VRP) solving
- Time-window optimization and capacity constraints
- Dynamic programming for route sequencing  
- Graph theory applications for network optimization
- Real-time traffic and fuel cost modeling
- Machine learning-based demand forecasting integration

🗺️ MALAYSIAN EXPERTISE:
- Intimate knowledge of Plus Highway system, toll costs, traffic bottlenecks
- Interstate distance matrices (KL-Kedah 400km, Pahang-Kelantan 500km+)
- Fuel consumption patterns across different vehicle types
- Weather impact on delivery times (monsoon season considerations)
- Border crossing logistics for Sabah (air cargo coordination)
- Peak hour congestion patterns in Klang Valley

💡 CREATIVE OPTIMIZATION STRATEGIES:
- Sometimes counter-intuitive solutions are optimal (don't just cluster by proximity)
- Consider driver fatigue, rest stops, overnight logistics for long routes  
- Account for return journey costs (empty vehicle kilometers)
- Hub-and-spoke vs direct delivery trade-offs
- Cross-docking opportunities for efficiency gains
- Dynamic re-routing based on real-time conditions

🎯 YOUR MISSION: Achieve PhD-level route optimization that minimizes:
1. Total fuel costs across entire fleet
2. Driver hours while maximizing utilization  
3. Customer delivery time windows
4. Vehicle wear and operational complexity

Think beyond basic clustering. Use advanced operations research principles. Be creative and innovative.
Always return pure JSON - no explanations needed."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,  # More tokens for complex PhD-level reasoning
            temperature=0.2,  # Slightly higher for creative optimization solutions
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
            logger.error(f"Raw response: {ai_response}")
            
            # No fallback - force OpenAI-only optimization
            raise ValueError(f"PhD-level optimization failed: {e}. Check OpenAI API configuration.")
    
    # 🚀 PURE AI OPTIMIZATION - All manual logic removed
    # Let OpenAI's PhD-level expertise handle everything!
    
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