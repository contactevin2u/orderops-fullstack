import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import (
    Driver,
    Customer,
    Order,
    Trip,
    TripEvent,
    DriverRoute,
    Role,
    DriverDevice,
)  # noqa: E402
from app.routers import orders as orders_router, routes as routes_router  # noqa: E402
from app.auth import firebase as auth_firebase  # noqa: E402
from tests.utils import setup_test_db, create_session_override  # noqa: E402




def test_assign_order_to_driver(monkeypatch):
    SessionLocal = setup_test_db()
    app.dependency_overrides[get_session] = create_session_override(SessionLocal)

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


def test_cannot_reassign_delivered_order(monkeypatch):
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
        driver1 = Driver(firebase_uid="u1", name="D1")
        driver2 = Driver(firebase_uid="u2", name="D2")
        customer = Customer(name="C1")
        db.add_all([driver1, driver2, customer])
        db.flush()
        order = Order(code="O1", type="OUTRIGHT", customer_id=customer.id)
        db.add(order)
        db.flush()
        trip = Trip(order_id=order.id, driver_id=driver1.id, status="DELIVERED")
        db.add(trip)
        db.commit()
        order_id = order.id
        driver2_id = driver2.id

    resp = client.post(f"/orders/{order_id}/assign", json={"driver_id": driver2_id})
    assert resp.status_code == 400

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
        order2 = Order(code="O2", type="OUTRIGHT", customer_id=customer.id)
        db.add_all([order, order2])
        db.flush()
        trip = Trip(order_id=order.id, driver_id=driver.id, status="ASSIGNED")
        trip2 = Trip(order_id=order2.id, driver_id=driver.id, status="DELIVERED")
        db.add_all([trip, trip2])
        db.commit()
        driver_id = driver.id
        order_id = order.id
        order2_id = order2.id

    app.dependency_overrides[auth_firebase.driver_auth] = lambda: driver

    client = TestClient(app)
    resp = client.get("/drivers/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert any(o["id"] == order_id for o in data)
    assert any(o["id"] == order2_id and o["status"] == "DELIVERED" for o in data)
    assert any(o["description"] == "O1" for o in data)

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

        resp = client.patch(f"/drivers/orders/{order_id}", json={"status": "ON_HOLD"})
        assert resp.status_code == 200

        with SessionLocal() as db:
            trip = db.query(Trip).filter_by(order_id=order_id).one()
            assert trip.status == "ON_HOLD"

        resp = client.patch(f"/drivers/orders/{order_id}", json={"status": "IN_TRANSIT"})
        assert resp.status_code == 200

        with SessionLocal() as db:
            trip = db.query(Trip).filter_by(order_id=order_id).one()
            assert trip.status == "IN_TRANSIT"
    finally:
        app.dependency_overrides.clear()


def test_routes_bulk_assign(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    class DummyUser:
        id = 1
        role = Role.ADMIN

    dep = routes_router.router.dependencies[0].dependency
    app.dependency_overrides[dep] = lambda: DummyUser()

    client = TestClient(app)

    with SessionLocal() as db:
        driver1 = Driver(firebase_uid="u1", name="D1")
        driver2 = Driver(firebase_uid="u2", name="D2")
        cust = Customer(name="C1")
        db.add_all([driver1, driver2, cust])
        db.flush()
        o1 = Order(code="O1", type="OUTRIGHT", customer_id=cust.id)
        o2 = Order(code="O2", type="OUTRIGHT", customer_id=cust.id)
        o3 = Order(code="O3", type="OUTRIGHT", customer_id=cust.id)
        o4 = Order(code="O4", type="OUTRIGHT", customer_id=cust.id)
        db.add_all([o1, o2, o3, o4])
        db.flush()
        t2 = Trip(order_id=o2.id, driver_id=driver2.id, status="ASSIGNED")
        t3 = Trip(order_id=o3.id, driver_id=driver2.id, status="DELIVERED")
        t4 = Trip(order_id=o4.id, driver_id=driver2.id, status="SUCCESS")
        db.add_all([t2, t3, t4])
        db.commit()
        driver1_id = driver1.id
        order_ids = [o1.id, o2.id, o3.id, o4.id]

    resp = client.post(
        "/routes",
        json={"driver_id": driver1_id, "route_date": "2024-01-01"},
    )
    assert resp.status_code == 200
    route_id = resp.json()["id"]

    resp = client.post(
        f"/routes/{route_id}/orders",
        json={"order_ids": order_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["assigned"]) == {order_ids[0], order_ids[1]}
    assert {tuple(x) for x in data["skipped"]} == {
        (order_ids[2], "delivered_or_success"),
        (order_ids[3], "delivered_or_success"),
    }

    with SessionLocal() as db:
        trip1 = db.query(Trip).filter_by(order_id=order_ids[0]).one()
        assert trip1.driver_id == driver1_id and trip1.route_id == route_id
        trip2 = db.query(Trip).filter_by(order_id=order_ids[1]).one()
        assert trip2.driver_id == driver1_id and trip2.route_id == route_id
        trip3 = db.query(Trip).filter_by(order_id=order_ids[2]).one()
        assert trip3.driver_id != driver1_id

    app.dependency_overrides.clear()


def test_pod_required(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with SessionLocal() as db:
        driver = Driver(firebase_uid="u1", name="D1")
        cust = Customer(name="C1")
        db.add_all([driver, cust])
        db.flush()
        order = Order(code="O1", type="OUTRIGHT", customer_id=cust.id)
        db.add(order)
        db.flush()
        trip = Trip(order_id=order.id, driver_id=driver.id, status="IN_TRANSIT")
        db.add(trip)
        db.commit()
        order_id = order.id

    app.dependency_overrides[auth_firebase.driver_auth] = lambda: driver

    client = TestClient(app)

    resp = client.patch(
        f"/drivers/orders/{order_id}", json={"status": "DELIVERED"}
    )
    assert resp.status_code == 400

    from PIL import Image
    import io

    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    resp = client.post(
        f"/drivers/orders/{order_id}/pod-photo",
        files={"file": ("p.jpg", buf.getvalue(), "image/jpeg")},
    )
    assert resp.status_code == 200

    resp = client.patch(
        f"/drivers/orders/{order_id}", json={"status": "DELIVERED"}
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        trip = db.query(Trip).filter_by(order_id=order_id).one()
        assert trip.delivered_at is not None
        assert trip.pod_photo_url is not None

    app.dependency_overrides.clear()
