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

@router.get("/assignment-test")
def test_assignment_service(db: Session = Depends(get_session)):
    """Test clean assignment service"""
    try:
        from ..services.assignment_service import AssignmentService
        
        service = AssignmentService(db)
        
        # Test getting available drivers and orders
        orders = service._get_orders_to_assign()
        drivers = service._get_available_drivers()
        
        return envelope({
            "orders_to_assign": orders,
            "orders_count": len(orders),
            "available_drivers": drivers,
            "drivers_count": len(drivers)
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

@router.post("/test-auto-assign")
def test_auto_assign(db: Session = Depends(get_session)):
    """Test auto-assignment without auth - for debugging only"""
    try:
        from ..services.assignment_service import AssignmentService
        
        service = AssignmentService(db)
        result = service.auto_assign_all()
        
        return envelope({
            "assignment_result": result,
            "success": result.get("success", False),
            "assigned_count": result.get("total", 0),
            "message": result.get("message", "")
        })
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@router.get("/debug-scheduled-drivers-query")
def debug_scheduled_drivers_query(db: Session = Depends(get_session)):
    """Debug the exact query used in assignment service"""
    try:
        from datetime import date
        from sqlalchemy import and_
        
        today = date.today()
        
        # Step 1: Check raw scheduled drivers table
        all_schedules = db.query(DriverSchedule).all()
        todays_schedules = db.query(DriverSchedule).filter(
            DriverSchedule.schedule_date == today
        ).all()
        todays_scheduled = db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.schedule_date == today,
                DriverSchedule.is_scheduled == True
            )
        ).all()
        
        # Step 2: Test the exact assignment service query step by step
        from ..services.assignment_service import AssignmentService
        service = AssignmentService(db)
        
        # Step 3: Try assignment service methods step by step to isolate the error
        assignment_debug = {}
        try:
            assignment_debug["service_created"] = True
            orders_to_assign = service._get_orders_to_assign()
            assignment_debug["orders_to_assign_count"] = len(orders_to_assign)
            assignment_debug["get_orders_success"] = True
        except Exception as e:
            assignment_debug["get_orders_error"] = str(e)
            assignment_debug["get_orders_success"] = False
            
        try:
            if assignment_debug.get("get_orders_success"):
                available_drivers = service._get_available_drivers()
                assignment_debug["available_drivers_count"] = len(available_drivers)
                assignment_debug["available_drivers"] = available_drivers
                assignment_debug["get_drivers_success"] = True
            else:
                assignment_debug["get_drivers_skipped"] = "orders query failed"
        except Exception as e:
            assignment_debug["get_drivers_error"] = str(e)
            assignment_debug["get_drivers_success"] = False
            import traceback
            assignment_debug["get_drivers_traceback"] = traceback.format_exc()

        return envelope({
            "debug_date": today.isoformat(),
            "raw_counts": {
                "all_schedules_in_db": len(all_schedules),
                "schedules_for_today": len(todays_schedules), 
                "scheduled_true_for_today": len(todays_scheduled)
            },
            "schedule_details": [
                {
                    "driver_id": s.driver_id,
                    "schedule_date": s.schedule_date.isoformat(),
                    "is_scheduled": s.is_scheduled,
                    "status": s.status
                } for s in todays_schedules
            ],
            "assignment_debug": assignment_debug
        })
        
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
        
        # Test 4: Assignment service instantiation
        from ..services.assignment_service import AssignmentService
        assignment_service = AssignmentService(db)
        
        result = {
            "raw_driver_count": total_count,
            "simple_query_count": len(simple_drivers),
            "drivers_endpoint_count": len(drivers_endpoint_logic),
            "assignment_service_created": True,
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
        
        # Test 5: Try assignment service methods individually
        try:
            available_drivers = assignment_service._get_available_drivers()
            result["assignment_available_drivers_count"] = len(available_drivers)
            result["assignment_available_drivers_error"] = None
        except Exception as e:
            result["assignment_available_drivers_count"] = "ERROR"
            result["assignment_available_drivers_error"] = str(e)
            
        return envelope(result)
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@router.get("/schedule-debug")  
def debug_schedule_alignment(db: Session = Depends(get_session)):
    """Debug schedule vs shift alignment issue"""
    try:
        from datetime import date, timedelta
        from sqlalchemy import and_
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Get all schedules around today
        all_schedules = db.query(DriverSchedule).filter(
            DriverSchedule.schedule_date.between(yesterday, tomorrow)
        ).all()
        
        # Get active shifts  
        active_shifts = db.query(DriverShift).filter(DriverShift.status == "ACTIVE").all()
        
        # Get all drivers
        all_drivers = db.query(Driver).filter(Driver.is_active == True).all()
        
        schedule_data = []
        for schedule in all_schedules:
            schedule_data.append({
                "driver_id": schedule.driver_id,
                "schedule_date": schedule.schedule_date.isoformat(),
                "is_scheduled": schedule.is_scheduled,
                "status": schedule.status
            })
        
        shift_data = []
        for shift in active_shifts:
            shift_data.append({
                "driver_id": shift.driver_id, 
                "status": shift.status,
                "clock_in_at": shift.clock_in_at.isoformat() if shift.clock_in_at else None
            })
            
        driver_data = []
        for driver in all_drivers:
            driver_data.append({
                "id": driver.id,
                "name": driver.name,
                "is_active": driver.is_active
            })
            
        return envelope({
            "today": today.isoformat(),
            "date_range": f"{yesterday.isoformat()} to {tomorrow.isoformat()}",
            "schedules_found": len(all_schedules),
            "schedules": schedule_data,
            "active_shifts_found": len(active_shifts), 
            "active_shifts": shift_data,
            "total_active_drivers": len(all_drivers),
            "drivers": driver_data
        })
        
    except Exception as e:
        import traceback
        return envelope({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
