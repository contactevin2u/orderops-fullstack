import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import (
    Base, SKU, Item, OrderItemUID, LorryStock, SKUAlias,
    Order, OrderItem, Driver, Customer
)


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Fix integer types for SQLite
    for model in [SKU, Item, OrderItemUID, LorryStock, SKUAlias, Order, OrderItem, Driver, Customer]:
        for column in model.__table__.columns:
            if hasattr(column.type, '__class__') and 'BigInteger' in str(column.type.__class__):
                column.type = Integer()
    
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_sku_model():
    """Test SKU model creation and relationships"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create a SKU
        sku = SKU(
            name="Test Product ABC",
            description="A test product for inventory",
            tracks_serial_numbers=True,
            is_serialized=True
        )
        session.add(sku)
        session.commit()
        session.refresh(sku)
        
        assert sku.id is not None
        assert sku.name == "Test Product ABC"
        assert sku.tracks_serial_numbers is True
        assert sku.is_serialized is True
        assert sku.created_at is not None


def test_item_model():
    """Test Item model creation and UID tracking"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create a SKU first
        sku = SKU(name="Test Item", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()
        session.refresh(sku)
        
        # Create an Item with UID
        item = Item(
            uid="TEST123456789",
            sku_id=sku.id,
            status="AVAILABLE",
            location="WAREHOUSE_A"
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        
        assert item.id is not None
        assert item.uid == "TEST123456789"
        assert item.sku_id == sku.id
        assert item.status == "AVAILABLE"
        assert item.location == "WAREHOUSE_A"
        assert item.created_at is not None


def test_order_item_uid_model():
    """Test OrderItemUID model for tracking UID actions"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create necessary dependencies
        customer = Customer(name="Test Customer", phone="123456789")
        session.add(customer)
        
        order = Order(
            code="TEST001",
            type="OUTRIGHT",
            customer_id=1,
            total=Decimal("100.00")
        )
        session.add(order)
        
        driver = Driver(
            name="Test Driver",
            firebase_uid="test_uid_123",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)
        
        sku = SKU(name="Test SKU", tracks_serial_numbers=True)
        session.add(sku)
        
        session.commit()
        session.refresh(order)
        session.refresh(driver)
        session.refresh(sku)
        
        # Create OrderItemUID
        order_item_uid = OrderItemUID(
            uid="UID123456789",
            order_id=order.id,
            action="ISSUE",
            sku_id=sku.id,
            driver_id=driver.id,
            notes="Initial issue for delivery"
        )
        session.add(order_item_uid)
        session.commit()
        session.refresh(order_item_uid)
        
        assert order_item_uid.id is not None
        assert order_item_uid.uid == "UID123456789"
        assert order_item_uid.order_id == order.id
        assert order_item_uid.action == "ISSUE"
        assert order_item_uid.sku_id == sku.id
        assert order_item_uid.driver_id == driver.id
        assert order_item_uid.notes == "Initial issue for delivery"
        assert order_item_uid.scanned_at is not None


def test_lorry_stock_model():
    """Test LorryStock model for daily stock tracking"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create dependencies
        driver = Driver(
            name="Stock Driver",
            firebase_uid="stock_uid_123",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)
        
        sku = SKU(name="Stock Item", tracks_serial_numbers=True)
        session.add(sku)
        
        session.commit()
        session.refresh(driver)
        session.refresh(sku)
        
        # Create LorryStock entry
        stock_date = datetime.now(timezone.utc).date()
        lorry_stock = LorryStock(
            driver_id=driver.id,
            date=stock_date,
            sku_id=sku.id,
            expected_quantity=10,
            counted_quantity=8,
            variance=-2
        )
        session.add(lorry_stock)
        session.commit()
        session.refresh(lorry_stock)
        
        assert lorry_stock.id is not None
        assert lorry_stock.driver_id == driver.id
        assert lorry_stock.date == stock_date
        assert lorry_stock.sku_id == sku.id
        assert lorry_stock.expected_quantity == 10
        assert lorry_stock.counted_quantity == 8
        assert lorry_stock.variance == -2
        assert lorry_stock.created_at is not None


def test_sku_alias_model():
    """Test SKUAlias model for name matching"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create SKU
        sku = SKU(name="Original Product Name", tracks_serial_numbers=False)
        session.add(sku)
        session.commit()
        session.refresh(sku)
        
        # Create aliases
        alias1 = SKUAlias(sku_id=sku.id, alias="Alternative Name")
        alias2 = SKUAlias(sku_id=sku.id, alias="Short Name")
        
        session.add_all([alias1, alias2])
        session.commit()
        
        session.refresh(alias1)
        session.refresh(alias2)
        
        assert alias1.id is not None
        assert alias1.sku_id == sku.id
        assert alias1.alias == "Alternative Name"
        
        assert alias2.id is not None
        assert alias2.sku_id == sku.id
        assert alias2.alias == "Short Name"


def test_model_relationships():
    """Test relationships between inventory models"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create all necessary models
        customer = Customer(name="Relationship Test", phone="123456789")
        session.add(customer)
        
        driver = Driver(
            name="Relationship Driver",
            firebase_uid="rel_uid_123",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)
        
        sku = SKU(name="Relationship SKU", tracks_serial_numbers=True)
        session.add(sku)
        
        order = Order(
            code="REL001",
            type="OUTRIGHT",
            customer_id=1,
            total=Decimal("150.00")
        )
        session.add(order)
        
        session.commit()
        session.refresh(customer)
        session.refresh(driver)
        session.refresh(sku)
        session.refresh(order)
        
        # Create related records
        item = Item(uid="REL123456", sku_id=sku.id, status="ISSUED")
        session.add(item)
        
        order_uid = OrderItemUID(
            uid="REL123456",
            order_id=order.id,
            action="ISSUE",
            sku_id=sku.id,
            driver_id=driver.id
        )
        session.add(order_uid)
        
        alias = SKUAlias(sku_id=sku.id, alias="Rel Alias")
        session.add(alias)
        
        session.commit()
        
        # Test relationships work
        session.refresh(sku)
        session.refresh(order)
        session.refresh(driver)
        
        # Check that relationships are accessible
        assert len(sku.aliases) == 1
        assert sku.aliases[0].alias == "Rel Alias"
        
        assert len(order.item_uids) == 1
        assert order.item_uids[0].uid == "REL123456"
        
        assert len(driver.scanned_items) == 1
        assert driver.scanned_items[0].uid == "REL123456"


def test_uid_uniqueness_constraint():
    """Test that UIDs must be unique within the system"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create dependencies
        customer = Customer(name="Test Customer", phone="123456789")
        session.add(customer)
        
        order = Order(
            code="UNIQUE001",
            type="OUTRIGHT", 
            customer_id=1,
            total=Decimal("100.00")
        )
        session.add(order)
        
        driver = Driver(
            name="Test Driver",
            firebase_uid="unique_uid",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)
        
        sku = SKU(name="Unique SKU", tracks_serial_numbers=True)
        session.add(sku)
        
        session.commit()
        session.refresh(order)
        session.refresh(driver) 
        session.refresh(sku)
        
        # Create first OrderItemUID
        uid1 = OrderItemUID(
            uid="DUPLICATE123",
            order_id=order.id,
            action="ISSUE",
            sku_id=sku.id,
            driver_id=driver.id
        )
        session.add(uid1)
        session.commit()
        
        # Try to create duplicate UID - this should fail
        uid2 = OrderItemUID(
            uid="DUPLICATE123",  # Same UID
            order_id=order.id,
            action="RETURN",
            sku_id=sku.id,
            driver_id=driver.id
        )
        session.add(uid2)
        
        try:
            session.commit()
            assert False, "Expected unique constraint violation"
        except Exception as e:
            session.rollback()
            assert "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e).lower()


if __name__ == "__main__":
    test_sku_model()
    test_item_model()
    test_order_item_uid_model()
    test_lorry_stock_model()
    test_sku_alias_model()
    test_model_relationships()
    test_uid_uniqueness_constraint()
    print("All UID inventory model tests passed!")