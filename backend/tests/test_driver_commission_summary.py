from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import (
    Base,
    Customer,
    Order,
    Driver,
    Trip,
    Commission,
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
    Commission.__table__.c.id.type = Integer()
    Commission.__table__.c.driver_id.type = Integer()
    Commission.__table__.c.trip_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            Driver.__table__,
            Trip.__table__,
            Commission.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_driver_commissions_monthly(monkeypatch):
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    from app.auth import firebase as fb

    def fake_verify(token):
        assert token == "good"
        return {"uid": "u1"}

    monkeypatch.setattr(fb, "verify_firebase_id_token", fake_verify)

    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="C", phone="1")
        db.add(cust)
        db.commit()
        db.refresh(cust)

        driver = Driver(firebase_uid="u1")
        db.add(driver)
        db.commit()
        db.refresh(driver)

        order1 = Order(code="O1", type="OUTRIGHT", customer_id=cust.id, total=Decimal("100"))
        db.add(order1)
        db.commit()
        db.refresh(order1)
        trip1 = Trip(order_id=order1.id, driver_id=driver.id, status="DELIVERED")
        db.add(trip1)
        db.commit()
        db.refresh(trip1)
        comm1 = Commission(
            driver_id=driver.id,
            trip_id=trip1.id,
            scheme="flat",
            rate=Decimal("10"),
            computed_amount=Decimal("10"),
            created_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
        )
        db.add(comm1)

        order2 = Order(code="O2", type="OUTRIGHT", customer_id=cust.id, total=Decimal("200"))
        db.add(order2)
        db.commit()
        db.refresh(order2)
        trip2 = Trip(order_id=order2.id, driver_id=driver.id, status="DELIVERED")
        db.add(trip2)
        db.commit()
        db.refresh(trip2)
        comm2 = Commission(
            driver_id=driver.id,
            trip_id=trip2.id,
            scheme="flat",
            rate=Decimal("20"),
            computed_amount=Decimal("20"),
            created_at=datetime(2024, 2, 5, tzinfo=timezone.utc),
        )
        db.add(comm2)

        db.commit()

    resp = client.get(
        "/drivers/commissions",
        headers={"Authorization": "Bearer good"},
    )
    assert resp.status_code == 200
    assert resp.json() == [
        {"month": "2024-01", "total": 10.0},
        {"month": "2024-02", "total": 20.0},
    ]

    app.dependency_overrides.clear()
