from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db import get_session
from ..models.user import User
from ..auth.deps import get_current_user
from typing import Dict, Any

router = APIRouter(prefix="/admin", tags=["admin-master"])


def verify_admin_access(current_user: User = Depends(get_current_user)) -> User:
    """Verify user has admin access for dangerous operations"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation"
        )
    return current_user


@router.delete("/delete-all-orders")
async def delete_all_orders(
    db: Session = Depends(get_session),
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    DANGER: Delete ALL orders and related data
    This will permanently remove:
    - All orders
    - All trips
    - All order items
    - All payments
    - All plans
    - All commission records
    """
    try:
        # Delete in proper order to respect foreign key constraints
        
        # Delete commission records
        db.execute(text("DELETE FROM commission_records"))
        
        # Delete trip location pings
        db.execute(text("DELETE FROM trip_location_pings"))
        
        # Delete trips
        db.execute(text("DELETE FROM trips"))
        
        # Delete payments
        db.execute(text("DELETE FROM payments"))
        
        # Delete order items
        db.execute(text("DELETE FROM order_items"))
        
        # Delete plans
        db.execute(text("DELETE FROM plans"))
        
        # Delete upsell incentives
        db.execute(text("DELETE FROM upsell_incentives"))
        
        # Delete order audit logs
        db.execute(text("DELETE FROM order_audit_logs"))
        
        # Finally delete orders
        result = db.execute(text("DELETE FROM orders"))
        orders_deleted = result.rowcount
        
        db.commit()
        
        return {
            "message": "All orders and related data deleted successfully",
            "orders_deleted": orders_deleted,
            "operation": "delete_all_orders",
            "performed_by": current_user.username
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete orders: {str(e)}"
        )


@router.delete("/delete-all-drivers")
async def delete_all_drivers(
    db: Session = Depends(get_session),
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    DANGER: Delete ALL drivers and related data
    This will permanently remove:
    - All driver accounts
    - All shifts
    - All driver location pings
    - Unassign all trips from drivers
    """
    try:
        # Get count before deletion
        driver_count_result = db.execute(text("SELECT COUNT(*) FROM drivers"))
        drivers_count = driver_count_result.scalar()
        
        # Update trips to remove driver assignments
        db.execute(text("UPDATE trips SET driver_id = NULL"))
        
        # Update routes to remove driver assignments
        db.execute(text("UPDATE routes SET driver_id = NULL, secondary_driver_id = NULL"))
        
        # Delete driver location pings
        db.execute(text("DELETE FROM driver_location_pings"))
        
        # Delete shifts
        db.execute(text("DELETE FROM shifts"))
        
        # Delete drivers
        db.execute(text("DELETE FROM drivers"))
        
        db.commit()
        
        return {
            "message": "All drivers and related data deleted successfully",
            "drivers_deleted": drivers_count,
            "operation": "delete_all_drivers",
            "performed_by": current_user.username
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete drivers: {str(e)}"
        )


@router.delete("/delete-all-routes")
async def delete_all_routes(
    db: Session = Depends(get_session),
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    DANGER: Delete ALL routes
    This will permanently remove:
    - All routes
    - Update trips to remove route assignments
    """
    try:
        # Get count before deletion
        route_count_result = db.execute(text("SELECT COUNT(*) FROM routes"))
        routes_count = route_count_result.scalar()
        
        # Update trips to remove route assignments
        db.execute(text("UPDATE trips SET route_id = NULL"))
        
        # Delete routes
        db.execute(text("DELETE FROM routes"))
        
        db.commit()
        
        return {
            "message": "All routes deleted successfully",
            "routes_deleted": routes_count,
            "operation": "delete_all_routes",
            "performed_by": current_user.username
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete routes: {str(e)}"
        )


@router.post("/reset-database")
async def reset_database(
    db: Session = Depends(get_session),
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """
    NUCLEAR OPTION: Reset entire database to factory state
    This will permanently remove ALL DATA except:
    - User accounts (to prevent lockout)
    - Database schema/structure
    
    WARNING: This action cannot be undone!
    """
    try:
        # Get counts before deletion
        counts_query = """
        SELECT 
            (SELECT COUNT(*) FROM orders) as orders,
            (SELECT COUNT(*) FROM drivers) as drivers,
            (SELECT COUNT(*) FROM routes) as routes,
            (SELECT COUNT(*) FROM trips) as trips,
            (SELECT COUNT(*) FROM payments) as payments,
            (SELECT COUNT(*) FROM shifts) as shifts
        """
        counts_result = db.execute(text(counts_query)).first()
        
        # Delete all data in proper order
        deletion_order = [
            "commission_records",
            "trip_location_pings",
            "driver_location_pings",
            "upsell_incentives",
            "order_audit_logs",
            "export_runs",
            "payments",
            "order_items", 
            "plans",
            "trips",
            "routes",
            "shifts",
            "drivers",
            "orders"
        ]
        
        for table in deletion_order:
            try:
                db.execute(text(f"DELETE FROM {table}"))
            except Exception:
                # Continue if table doesn't exist or other errors
                pass
        
        # Reset auto-increment sequences (PostgreSQL)
        try:
            sequences = [
                "orders_id_seq",
                "drivers_id_seq", 
                "routes_id_seq",
                "trips_id_seq",
                "payments_id_seq",
                "shifts_id_seq",
                "users_id_seq"
            ]
            
            for seq in sequences:
                try:
                    db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                except Exception:
                    # Continue if sequence doesn't exist
                    pass
                    
        except Exception:
            # If not PostgreSQL, sequences might not exist
            pass
        
        db.commit()
        
        return {
            "message": "Database reset completed successfully",
            "deleted_counts": {
                "orders": counts_result.orders if counts_result else 0,
                "drivers": counts_result.drivers if counts_result else 0,
                "routes": counts_result.routes if counts_result else 0,
                "trips": counts_result.trips if counts_result else 0,
                "payments": counts_result.payments if counts_result else 0,
                "shifts": counts_result.shifts if counts_result else 0
            },
            "operation": "nuclear_reset",
            "performed_by": current_user.username,
            "warning": "All operational data has been permanently deleted"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )


@router.get("/system-stats")
async def get_system_stats(
    db: Session = Depends(get_session),
    current_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Get current system statistics for verification"""
    try:
        stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM orders) as total_orders,
            (SELECT COUNT(*) FROM drivers) as total_drivers,
            (SELECT COUNT(*) FROM routes) as total_routes,
            (SELECT COUNT(*) FROM trips) as total_trips,
            (SELECT COUNT(*) FROM payments) as total_payments,
            (SELECT COUNT(*) FROM shifts) as total_shifts,
            (SELECT COUNT(*) FROM users) as total_users
        """
        result = db.execute(text(stats_query)).first()
        
        return {
            "system_stats": {
                "orders": result.total_orders if result else 0,
                "drivers": result.total_drivers if result else 0,
                "routes": result.total_routes if result else 0,
                "trips": result.total_trips if result else 0,
                "payments": result.total_payments if result else 0,
                "shifts": result.total_shifts if result else 0,
                "users": result.total_users if result else 0
            },
            "timestamp": "2025-01-03T00:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}"
        )