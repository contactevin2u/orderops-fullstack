"""
Performance optimization indexes for OrderOps
Run this after model creation: alembic revision --autogenerate -m "add_performance_indexes"
"""

from sqlalchemy import Index
from .order import Order
from .trip import Trip
from .payment import Payment
from .driver_shift import DriverShift
from .driver_schedule import DriverSchedule

# Critical composite indexes for auto-assignment queries
PERFORMANCE_INDEXES = [
    # Order listing with status/type/date filters (orders.py:129-162)
    Index('ix_orders_status_type_delivery', Order.status, Order.type, Order.delivery_date),
    Index('ix_orders_parent_status', Order.parent_id, Order.status),
    
    # Trip assignment queries (assignment_service.py:94-110) 
    Index('ix_trips_order_route', Trip.order_id, Trip.route_id),
    Index('ix_trips_driver_status', Trip.driver_id, Trip.status),
    
    # Payment queries for outstanding calculations
    Index('ix_payments_order_status_date', Payment.order_id, Payment.status, Payment.date),
    
    # Driver availability queries
    Index('ix_driver_shifts_driver_status', DriverShift.driver_id, DriverShift.status),
    Index('ix_driver_schedule_date_scheduled', DriverSchedule.schedule_date, DriverSchedule.is_scheduled),
]

# Apply indexes to models
for idx in PERFORMANCE_INDEXES:
    # Index will be created during migration
    pass