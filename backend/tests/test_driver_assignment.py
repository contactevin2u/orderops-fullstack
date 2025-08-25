import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Driver, Customer, Order, Trip, TripEvent, Role  # noqa: E402
from app.routers import orders as orders_router  # noqa: E402
from app.auth import firebase as auth_firebase  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Driver.__table__.c.id.type = Integer()
    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Order.__table__.c.customer_id.type = Integer()
    Trip.__table__.c.id.type = Integer()
    Trip.__table__.c.order_id.type = Integer()
    Trip.__table__.c.driver_id.type = Integer()
    TripEvent.__table__.c.id.type = Integer()
    TripEvent.__table__.c.trip_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Driver.__table__,
            Customer.__table__,
            Order.__table__,
            Trip.__table__,
            TripEvent.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_assign_order_to_driver(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    dep = orders_router.router.dependencies[0].dependency
    app.dependency_overrides[dep] = lambda: DummyUser()

    client = TestClient(app)

    with SessionLocal() as db:
        driver = Driver(firebase_uid="u1", name="D1")
        customer = Customer(name="C1")
        db.add_all([driver, customer])
        db.flush()
        order = Order(code="O1", type="OUTRIGHT", customer_id=customer.id)
        db.add(order)
        db.commit()
        driver_id = driver.id
        order_id = order.id

    resp = client.get("/drivers")
    assert resp.status_code == 200
    assert any(d["id"] == driver_id for d in resp.json())

    resp = client.post(f"/orders/{order_id}/assign", json={"driver_id": driver_id})
    assert resp.status_code == 200
    assert resp.json()["data"]["driver_id"] == driver_id

    with SessionLocal() as db:
        trip = db.query(Trip).filter_by(order_id=order_id).one()
        assert trip.driver_id == driver_id

    app.dependency_overrides.clear()


def test_driver_order_listing(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with SessionLocal() as db:
        driver = Driver(firebase_uid="u1", name="D1")
        customer = Customer(name="C1")
        db.add_all([driver, customer])
        db.flush()
        order = Order(code="O1", type="OUTRIGHT", customer_id=customer.id)
        db.add(order)
        db.flush()
        trip = Trip(order_id=order.id, driver_id=driver.id, status="ASSIGNED")
        db.add(trip)
        db.commit()
        driver_id = driver.id
        order_id = order.id

    app.dependency_overrides[auth_firebase.driver_auth] = lambda: driver

    client = TestClient(app)
    resp = client.get("/drivers/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert any(o["id"] == order_id for o in data)
    assert data[0]["description"] == "O1"
    assert data[0]["status"] == "ASSIGNED"

    app.dependency_overrides.clear()


def test_driver_can_update_order_status(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with SessionLocal() as db:
        driver = Driver(firebase_uid="u1", name="D1")
        customer = Customer(name="C1")
        db.add_all([driver, customer])
        db.flush()
        order = Order(code="O1", type="OUTRIGHT", customer_id=customer.id)
        db.add(order)
        db.flush()
        trip = Trip(order_id=order.id, driver_id=driver.id, status="ASSIGNED")
        db.add(trip)
        db.commit()
        order_id = order.id

    app.dependency_overrides[auth_firebase.driver_auth] = lambda: driver

    client = TestClient(app)
    try:
        resp = client.patch(f"/drivers/orders/{order_id}", json={"status": "IN_TRANSIT"})
        assert resp.status_code == 200

        with SessionLocal() as db:
            trip = db.query(Trip).filter_by(order_id=order_id).one()
            assert trip.status == "IN_TRANSIT"
            assert trip.started_at is not None

        resp = client.patch(f"/drivers/orders/{order_id}", json={"status": "DELIVERED"})
        assert resp.status_code == 200

        with SessionLocal() as db:
            trip = db.query(Trip).filter_by(order_id=order_id).one()
            assert trip.status == "DELIVERED"
            assert trip.delivered_at is not None
    finally:
        app.dependency_overrides.clear()
