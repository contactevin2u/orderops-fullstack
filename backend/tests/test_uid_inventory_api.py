import sys
from pathlib import Path
import json
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.db import get_session
from app.models import (
    Base, Order, Customer, Driver, SKU, Item, OrderItemUID, 
    LorryStock, SKUAlias, Role
)
from app.auth.deps import get_current_user


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Fix integer types for SQLite
    for model in [Order, Customer, Driver, SKU, Item, OrderItemUID, LorryStock, SKUAlias]:
        for column in model.__table__.columns:
            if hasattr(column.type, '__class__') and 'BigInteger' in str(column.type.__class__):
                column.type = Integer()
    
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_inventory_config_endpoint():
    """Test the inventory config endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    with patch('app.core.config.settings') as mock_settings:
        mock_settings.UID_INVENTORY_ENABLED = True
        mock_settings.UID_SCAN_REQUIRED_AFTER_POD = False
        mock_settings.uid_inventory_mode = "optional"

        client = TestClient(app)
        response = client.get("/inventory/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["uid_inventory_enabled"] is True
        assert data["uid_scan_required_after_pod"] is False
        assert data["inventory_mode"] == "optional"


def test_uid_scan_endpoint():
    """Test UID scanning endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        customer = Customer(name="Test Customer", phone="123456789")
        session.add(customer)
        session.commit()

        order = Order(
            code="SCAN001",
            type="OUTRIGHT",
            customer_id=customer.id,
            total=Decimal("100.00")
        )
        session.add(order)

        driver = Driver(
            name="Test Driver",
            firebase_uid="scan_test_uid",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)

        sku = SKU(name="Scannable Item", tracks_serial_numbers=True)
        session.add(sku)
        
        session.commit()

    client = TestClient(app)
    
    # Test UID scanning
    scan_data = {
        "order_id": 1,
        "action": "ISSUE",
        "uid": "SCAN123456789",
        "sku_id": 1,
        "notes": "Test scan"
    }
    
    response = client.post("/inventory/uid/scan", json=scan_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["uid"] == "SCAN123456789"
    assert data["action"] == "ISSUE"
    assert "message" in data


def test_uid_scan_duplicate_prevention():
    """Test that duplicate UID scanning is prevented"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        customer = Customer(name="Test Customer", phone="123456789")
        session.add(customer)

        order = Order(
            code="DUP001",
            type="OUTRIGHT",
            customer_id=1,
            total=Decimal("100.00")
        )
        session.add(order)

        driver = Driver(
            name="Test Driver",
            firebase_uid="dup_test_uid",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)

        sku = SKU(name="Duplicate Item", tracks_serial_numbers=True)
        session.add(sku)

        # Pre-existing UID
        existing_uid = OrderItemUID(
            uid="DUPLICATE123",
            order_id=1,
            action="ISSUE",
            sku_id=1,
            driver_id=1
        )
        session.add(existing_uid)
        
        session.commit()

    client = TestClient(app)
    
    # Try to scan the same UID again
    scan_data = {
        "order_id": 1,
        "action": "RETURN",
        "uid": "DUPLICATE123",
        "sku_id": 1
    }
    
    response = client.post("/inventory/uid/scan", json=scan_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_lorry_stock_endpoint():
    """Test lorry stock retrieval endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        driver = Driver(
            name="Stock Driver",
            firebase_uid="stock_test_uid",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)

        sku1 = SKU(name="Stock Item 1", tracks_serial_numbers=True)
        sku2 = SKU(name="Stock Item 2", tracks_serial_numbers=True)
        session.add_all([sku1, sku2])
        session.commit()

        # Add stock entries
        stock_date = datetime.now(timezone.utc).date()
        stock1 = LorryStock(
            driver_id=driver.id,
            date=stock_date,
            sku_id=sku1.id,
            expected_quantity=10,
            counted_quantity=8,
            variance=-2
        )
        stock2 = LorryStock(
            driver_id=driver.id,
            date=stock_date,
            sku_id=sku2.id,
            expected_quantity=5,
            counted_quantity=5,
            variance=0
        )
        session.add_all([stock1, stock2])
        session.commit()

    client = TestClient(app)
    
    # Test stock retrieval
    response = client.get(f"/drivers/{driver.id}/lorry-stock/{stock_date}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["driver_id"] == driver.id
    assert data["date"] == str(stock_date)
    assert len(data["items"]) == 2
    assert data["total_expected"] == 15
    assert data["total_scanned"] == 13
    assert data["total_variance"] == -2


def test_sku_resolve_endpoint():
    """Test SKU name resolution endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        sku = SKU(name="Exact Match Product", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()

        alias = SKUAlias(sku_id=sku.id, alias="Product Alias")
        session.add(alias)
        session.commit()

    client = TestClient(app)
    
    # Test exact match
    resolve_data = {"name": "Exact Match Product"}
    response = client.post("/inventory/sku/resolve", json=resolve_data)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) >= 1
    
    exact_match = next((m for m in data["matches"] if m["match_type"] == "exact"), None)
    assert exact_match is not None
    assert exact_match["sku_name"] == "Exact Match Product"
    assert exact_match["confidence"] == 1.0

    # Test alias match
    resolve_data = {"name": "Product Alias"}
    response = client.post("/inventory/sku/resolve", json=resolve_data)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) >= 1
    
    alias_match = next((m for m in data["matches"] if m["match_type"] == "alias"), None)
    assert alias_match is not None


def test_sku_alias_creation():
    """Test SKU alias creation endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        sku = SKU(name="Alias Test Product", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()

    client = TestClient(app)
    
    # Test alias creation
    alias_data = {
        "sku_id": 1,
        "alias": "New Product Alias"
    }
    response = client.post("/inventory/sku/alias", json=alias_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "alias_id" in data


def test_lorry_stock_upload():
    """Test lorry stock upload endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.DRIVER  # Driver uploading their own stock

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        driver = Driver(
            id=1,  # Match DummyUser id
            name="Upload Driver",
            firebase_uid="upload_test_uid",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)

        sku1 = SKU(name="Upload Item 1", tracks_serial_numbers=True)
        sku2 = SKU(name="Upload Item 2", tracks_serial_numbers=True)
        session.add_all([sku1, sku2])
        
        session.commit()

    client = TestClient(app)
    
    # Test stock upload
    upload_data = {
        "date": str(datetime.now(timezone.utc).date()),
        "stock_data": [
            {"sku_id": 1, "counted_quantity": 5},
            {"sku_id": 2, "counted_quantity": 3}
        ]
    }
    
    response = client.post("/inventory/lorry-stock/upload", json=upload_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["items_processed"] == 2


def test_order_uids_endpoint():
    """Test order UIDs retrieval endpoint"""
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Setup test data
    with SessionLocal() as session:
        customer = Customer(name="UID Test Customer", phone="123456789")
        session.add(customer)

        order = Order(
            code="UID001",
            type="OUTRIGHT",
            customer_id=1,
            total=Decimal("100.00")
        )
        session.add(order)

        driver = Driver(
            name="UID Driver",
            firebase_uid="uid_test_driver",
            base_warehouse="BATU_CAVES"
        )
        session.add(driver)

        sku = SKU(name="UID Item", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()

        # Add some UIDs
        uid1 = OrderItemUID(
            uid="ORDER_UID_001",
            order_id=order.id,
            action="ISSUE",
            sku_id=sku.id,
            driver_id=driver.id
        )
        uid2 = OrderItemUID(
            uid="ORDER_UID_002", 
            order_id=order.id,
            action="RETURN",
            sku_id=sku.id,
            driver_id=driver.id
        )
        session.add_all([uid1, uid2])
        session.commit()

    client = TestClient(app)
    
    # Test UIDs retrieval
    response = client.get(f"/orders/{order.id}/uids")
    assert response.status_code == 200
    
    data = response.json()
    assert data["order_id"] == order.id
    assert len(data["uids"]) == 2
    assert data["total_issued"] == 1
    assert data["total_returned"] == 1


if __name__ == "__main__":
    test_inventory_config_endpoint()
    test_uid_scan_endpoint()
    test_uid_scan_duplicate_prevention()
    test_lorry_stock_endpoint()
    test_sku_resolve_endpoint()
    test_sku_alias_creation()
    test_lorry_stock_upload()
    test_order_uids_endpoint()
    print("All UID inventory API tests passed!")