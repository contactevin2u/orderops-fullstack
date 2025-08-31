"""Debug endpoints to diagnose database issues"""

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..db import get_session
from ..models.driver import Driver
from ..models.driver_shift import DriverShift  
from ..models.driver_schedule import DriverSchedule, DriverAvailabilityPattern
from ..models.order import Order
from ..models.trip import Trip
from ..services.driver_schedule_service import DriverScheduleService
from ..utils.responses import envelope

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/database-status")
def get_database_status(db: Session = Depends(get_session)):
    """Get database status and counts"""
    try:
        # Count all key entities
        driver_count = db.query(Driver).count()
        active_driver_count = db.query(Driver).filter(Driver.is_active == True).count()
        shift_count = db.query(DriverShift).count()
        active_shift_count = db.query(DriverShift).filter(DriverShift.status == "ACTIVE").count()
        schedule_count = db.query(DriverSchedule).count()
        pattern_count = db.query(DriverAvailabilityPattern).count()
        order_count = db.query(Order).count()
        trip_count = db.query(Trip).count()
        
        # Get sample data
        sample_drivers = db.query(Driver).limit(5).all()
        sample_shifts = db.query(DriverShift).limit(5).all()
        sample_schedules = db.query(DriverSchedule).limit(5).all()
        
        return envelope({
            "counts": {
                "drivers": driver_count,
                "active_drivers": active_driver_count,
                "shifts": shift_count,
                "active_shifts": active_shift_count,
                "schedules": schedule_count,
                "patterns": pattern_count,
                "orders": order_count,
                "trips": trip_count
            },
            "sample_drivers": [
                {
                    "id": d.id,
                    "name": d.name,
                    "phone": d.phone,
                    "firebase_uid": d.firebase_uid,
                    "is_active": d.is_active
                } for d in sample_drivers
            ],
            "sample_shifts": [
                {
                    "id": s.id,
                    "driver_id": s.driver_id,
                    "status": s.status,
                    "clock_in_at": s.clock_in_at.isoformat() if s.clock_in_at else None,
                    "clock_out_at": s.clock_out_at.isoformat() if s.clock_out_at else None
                } for s in sample_shifts
            ],
            "sample_schedules": [
                {
                    "id": s.id,
                    "driver_id": s.driver_id,
                    "schedule_date": s.schedule_date.isoformat(),
                    "is_scheduled": s.is_scheduled,
                    "status": s.status
                } for s in sample_schedules
            ]
        })
    except Exception as e:
        return envelope({"error": str(e)})

@router.get("/schedule-test")
def test_schedule_service(db: Session = Depends(get_session)):
    """Test schedule service functionality"""
    try:
        schedule_service = DriverScheduleService(db)
        today = date.today()
        
        # Test getting scheduled drivers for today
        scheduled_drivers = schedule_service.get_scheduled_drivers_for_date(today)
        
        # Test getting schedule summary
        summary = schedule_service.get_schedule_summary(today)
        
        return envelope({
            "date": today.isoformat(),
            "scheduled_drivers": scheduled_drivers,
            "summary": summary,
            "scheduled_count": len(scheduled_drivers)
        })
    except Exception as e:
        return envelope({"error": str(e), "traceback": str(e.__traceback__)})

@router.get("/ai-assignment-test")
def test_ai_assignment_service(db: Session = Depends(get_session)):
    """Test AI assignment service"""
    try:
        from ..services.ai_assignment_service import AIAssignmentService
        
        ai_service = AIAssignmentService(db)
        
        # Test getting available drivers
        available_drivers = ai_service.get_available_drivers()
        
        # Test getting pending orders
        pending_orders = ai_service.get_pending_orders()
        
        return envelope({
            "available_drivers": available_drivers,
            "available_drivers_count": len(available_drivers),
            "pending_orders": pending_orders,
            "pending_orders_count": len(pending_orders)
        })
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e), 
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        })

@router.get("/raw-driver-data")  
def get_raw_driver_data(db: Session = Depends(get_session)):
    """Get raw driver data without any scheduling logic"""
    try:
        # Get basic counts without complex queries
        from sqlalchemy import text
        
        result = {}
        
        # Raw SQL queries to avoid any model issues
        result["drivers_raw"] = db.execute(text("SELECT COUNT(*) FROM drivers")).scalar()
        result["active_drivers_raw"] = db.execute(text("SELECT COUNT(*) FROM drivers WHERE is_active = true")).scalar()
        
        try:
            result["shifts_raw"] = db.execute(text("SELECT COUNT(*) FROM driver_shifts")).scalar()
            result["active_shifts_raw"] = db.execute(text("SELECT COUNT(*) FROM driver_shifts WHERE status = 'ACTIVE'")).scalar()
        except Exception:
            result["shifts_error"] = "driver_shifts table may not exist"
        
        try:
            result["schedules_raw"] = db.execute(text("SELECT COUNT(*) FROM driver_schedules")).scalar()
            result["patterns_raw"] = db.execute(text("SELECT COUNT(*) FROM driver_availability_patterns")).scalar()
        except Exception:
            result["schedules_error"] = "driver schedule tables may not exist"
        
        # Get some sample driver data
        try:
            driver_samples = db.execute(text("SELECT id, name, phone, firebase_uid, is_active FROM drivers LIMIT 5")).fetchall()
            result["sample_drivers"] = [
                {
                    "id": row[0],
                    "name": row[1], 
                    "phone": row[2],
                    "firebase_uid": row[3],
                    "is_active": row[4]
                } for row in driver_samples
            ]
        except Exception as e:
            result["driver_sample_error"] = str(e)
        
        return envelope(result)
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@router.post("/create-test-drivers")
def create_test_drivers(count: int = 3, db: Session = Depends(get_session)):
    """Create test drivers if none exist - for debugging only"""
    try:
        from ..models.driver import Driver
        import uuid
        
        # Check if drivers already exist
        existing_count = db.query(Driver).count()
        if existing_count > 0:
            return envelope({
                "message": f"Drivers already exist ({existing_count} found). Not creating test drivers.",
                "existing_count": existing_count
            })
        
        # Create test drivers
        created_drivers = []
        for i in range(count):
            driver = Driver(
                name=f"Test Driver {i+1}",
                phone=f"+6010000000{i+1}",
                firebase_uid=f"test_driver_{uuid.uuid4().hex[:8]}",
                is_active=True
            )
            db.add(driver)
            created_drivers.append({
                "name": driver.name,
                "phone": driver.phone,
                "firebase_uid": driver.firebase_uid
            })
        
        db.commit()
        
        return envelope({
            "message": f"Created {count} test drivers",
            "drivers": created_drivers
        })
        
    except Exception as e:
        db.rollback()
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@router.get("/order-54-debug")
def debug_order_54(db: Session = Depends(get_session)):
    """Debug order 54 specifically"""
    try:
        from datetime import date
        today = date.today()
        
        # Get order 54
        order_54 = db.query(Order).filter(Order.id == 54).first()
        if not order_54:
            return envelope({"error": "Order 54 not found"})
        
        # Get trip for order 54
        trip_54 = db.query(Trip).filter(Trip.order_id == 54).first()
        
        # Check filtering conditions individually
        status_check = order_54.status in ["NEW", "PENDING"]
        date_check = order_54.delivery_date is None or (order_54.delivery_date and order_54.delivery_date.date() == today)
        assignment_check = trip_54 is None or trip_54.route_id is None
        
        # Test the exact query from SmartAssignmentService
        from sqlalchemy import and_, or_
        from sqlalchemy.orm import joinedload
        
        test_query = (
            db.query(Order)
            .options(joinedload(Order.customer))
            .outerjoin(Trip, Trip.order_id == Order.id)
            .filter(
                and_(
                    Order.id == 54,  # Only order 54
                    Order.status.in_(["NEW", "PENDING"]),
                    or_(
                        Order.delivery_date == today,
                        Order.delivery_date.is_(None)
                    ),
                    or_(Trip.id.is_(None), Trip.route_id.is_(None))
                )
            )
            .all()
        )
        
        return envelope({
            "order_54": {
                "id": order_54.id,
                "code": order_54.code,
                "status": order_54.status,
                "delivery_date": order_54.delivery_date.date().isoformat() if order_54.delivery_date else None,
                "customer_name": order_54.customer.name if order_54.customer else None
            },
            "trip_54": {
                "id": trip_54.id if trip_54 else None,
                "driver_id": trip_54.driver_id if trip_54 else None,
                "route_id": trip_54.route_id if trip_54 else None,
                "status": trip_54.status if trip_54 else None
            } if trip_54 else None,
            "filtering_checks": {
                "status_check": status_check,
                "date_check": date_check,
                "assignment_check": assignment_check,
                "all_pass": status_check and date_check and assignment_check
            },
            "query_result": {
                "found_by_query": len(test_query) > 0,
                "count": len(test_query)
            },
            "today": today.isoformat()
        })
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@router.get("/simple-driver-test")
def simple_driver_test(db: Session = Depends(get_session)):
    """Dead simple driver test - bypass all complex logic"""
    try:
        # Test 1: Raw driver count
        total_count = db.execute(text("SELECT COUNT(*) FROM drivers")).scalar()
        
        # Test 2: Simple driver query
        simple_drivers = db.query(Driver).all()
        
        # Test 3: Working /drivers endpoint logic
        drivers_endpoint_logic = db.query(Driver).filter(Driver.is_active == True).limit(1000).all()
        
        # Test 4: AI service instantiation
        from ..services.ai_assignment_service import AIAssignmentService
        ai_service = AIAssignmentService(db)
        
        result = {
            "raw_driver_count": total_count,
            "simple_query_count": len(simple_drivers),
            "drivers_endpoint_count": len(drivers_endpoint_logic),
            "ai_service_created": True,
            "sample_drivers": []
        }
        
        # Get sample driver data
        for driver in simple_drivers[:3]:
            result["sample_drivers"].append({
                "id": driver.id,
                "name": driver.name,
                "phone": driver.phone,
                "firebase_uid": driver.firebase_uid,
                "is_active": driver.is_active
            })
        
        # Test 5: Try AI service methods individually
        try:
            available_drivers = ai_service.get_available_drivers()
            result["ai_available_drivers_count"] = len(available_drivers)
            result["ai_available_drivers_error"] = None
        except Exception as e:
            result["ai_available_drivers_count"] = "ERROR"
            result["ai_available_drivers_error"] = str(e)
            
        return envelope(result)
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })