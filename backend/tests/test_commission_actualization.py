import sys
from pathlib import Path
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
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
)  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import Integer

    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Order.__table__.c.customer_id.type = Integer()
    Driver.__table__.c.id.type = Integer()
    Trip.__table__.c.id.type = Integer()
    Trip.__table__.c.order_id.type = Integer()
    Trip.__table__.c.driver_id.type = Integer()
    DriverRoute.__table__.c.id.type = Integer()
    DriverRoute.__table__.c.driver_id.type = Integer()
    Trip.__table__.c.route_id.type = Integer()
    Commission.__table__.c.id.type = Integer()
    Commission.__table__.c.driver_id.type = Integer()
    Commission.__table__.c.trip_id.type = Integer()
    OrderItem.__table__.c.id.type = Integer()
    OrderItem.__table__.c.order_id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Plan.__table__.c.order_id.type = Integer()
    Payment.__table__.c.id.type = Integer()
    Payment.__table__.c.order_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            Driver.__table__,
            DriverRoute.__table__,
            Trip.__table__,
            Commission.__table__,
            OrderItem.__table__,
            Plan.__table__,
            Payment.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_commission_on_success(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="C", phone="1")
        db.add(cust)
        db.commit()
        db.refresh(cust)

        order = Order(code="O1", type="OUTRIGHT", customer_id=cust.id, total=Decimal("600"))
        db.add(order)
        db.commit()
        db.refresh(order)

        driver = Driver(firebase_uid="u1")
        db.add(driver)
        db.commit()
        db.refresh(driver)

        trip = Trip(order_id=order.id, driver_id=driver.id, status="DELIVERED")
        db.add(trip)
        db.commit()
        db.refresh(trip)

    resp = client.post(f"/orders/{order.id}/success")
    assert resp.status_code == 200

    with SessionLocal() as db:
        commission = db.query(Commission).first()
        assert commission.actualized_at is not None
        assert commission.computed_amount == Decimal("30.00")
        assert commission.actualization_reason == "manual_success"

    resp = client.patch(
        f"/orders/{order.id}/commission", json={"amount": 40}
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        commission = db.query(Commission).first()
        assert commission.computed_amount == Decimal("40.00")

    app.dependency_overrides.clear()


def test_update_commission_creates_and_pod_included(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="C", phone="1")
        db.add(cust)
        db.commit()
        db.refresh(cust)

        order = Order(code="O2", type="OUTRIGHT", customer_id=cust.id, total=Decimal("500"))
        db.add(order)
        db.commit()
        db.refresh(order)

        driver = Driver(firebase_uid="u2")
        db.add(driver)
        db.commit()
        db.refresh(driver)

        trip = Trip(order_id=order.id, driver_id=driver.id, status="DELIVERED", pod_photo_url="http://pod")
        db.add(trip)
        db.commit()
        db.refresh(trip)

    resp = client.patch(f"/orders/{order.id}/commission", json={"amount": 25})
    assert resp.status_code == 200

    with SessionLocal() as db:
        commission = db.query(Commission).filter_by(trip_id=trip.id).one()
        assert commission.computed_amount == Decimal("25.00")

    resp = client.get(f"/orders?driver_id={driver.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["trip"]["pod_photo_url"] == "http://pod"

    app.dependency_overrides.clear()
