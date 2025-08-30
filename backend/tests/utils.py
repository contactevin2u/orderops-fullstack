"""Shared test utilities to reduce code duplication across test files."""

from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base,
    Customer,
    Order,
    Driver,
    Trip,
    DriverRoute,
    Commission,
    OrderItem,
    Plan,
    Payment,
    TripEvent,
    Role,
    DriverDevice,
    User,
    AuditLogEntry,
    ExportRun,
    ExportRunFile,
)


def setup_test_db():
    """Create a test database with proper SQLite integer type mapping."""
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Map BigInteger columns to Integer for SQLite compatibility
    _map_bigint_to_int()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_session_override(SessionLocal):
    """Create a session override function for dependency injection in tests."""
    def override_get_session():
        with SessionLocal() as session:
            yield session
    return override_get_session


def _map_bigint_to_int():
    """Map BigInteger columns to Integer for SQLite test compatibility."""
    # Core entities
    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Order.__table__.c.customer_id.type = Integer()
    Driver.__table__.c.id.type = Integer()
    Trip.__table__.c.id.type = Integer()
    Trip.__table__.c.order_id.type = Integer()
    Trip.__table__.c.driver_id.type = Integer()
    Trip.__table__.c.driver_id_2.type = Integer()  # New dual driver support
    
    # Routes and commissions
    DriverRoute.__table__.c.id.type = Integer()
    DriverRoute.__table__.c.driver_id.type = Integer()
    Trip.__table__.c.route_id.type = Integer()
    Commission.__table__.c.id.type = Integer()
    Commission.__table__.c.driver_id.type = Integer()
    Commission.__table__.c.trip_id.type = Integer()
    
    # Order items and plans
    OrderItem.__table__.c.id.type = Integer()
    OrderItem.__table__.c.order_id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Plan.__table__.c.order_id.type = Integer()
    
    # Payments and events
    Payment.__table__.c.id.type = Integer()
    Payment.__table__.c.order_id.type = Integer()
    TripEvent.__table__.c.id.type = Integer()
    TripEvent.__table__.c.trip_id.type = Integer()
    
    # Admin and audit
    User.__table__.c.id.type = Integer()
    Role.__table__.c.id.type = Integer()
    DriverDevice.__table__.c.id.type = Integer()
    DriverDevice.__table__.c.driver_id.type = Integer()
    AuditLogEntry.__table__.c.id.type = Integer()
    
    # Export system
    ExportRun.__table__.c.id.type = Integer()
    ExportRunFile.__table__.c.id.type = Integer()
    ExportRunFile.__table__.c.export_run_id.type = Integer()