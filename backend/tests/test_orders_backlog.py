import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import (
    Base,
    Customer,
    Order,
    Driver,
    Trip,
    OrderItem,
    Payment,
    Plan,
    Role,
)  # noqa: E402
from app.routers import orders as orders_router  # noqa: E402


APP_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Order.__table__.c.customer_id.type = Integer()
    Driver.__table__.c.id.type = Integer()
    Trip.__table__.c.id.type = Integer()
    Trip.__table__.c.order_id.type = Integer()
    Trip.__table__.c.driver_id.type = Integer()
    Trip.__table__.c.route_id.type = Integer()
    OrderItem.__table__.c.id.type = Integer()
    OrderItem.__table__.c.order_id.type = Integer()
    Payment.__table__.c.id.type = Integer()
    Payment.__table__.c.order_id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Plan.__table__.c.order_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            Driver.__table__,
            Trip.__table__,
            OrderItem.__table__,
            Payment.__table__,
            Plan.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def _override_auth():
    class DummyUser:
        id = 1
        role = Role.ADMIN

    dep = orders_router.router.dependencies[0].dependency
    app.dependency_overrides[dep] = lambda: DummyUser()


def test_unassigned_backlog_includes_null_and_overdue():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    _override_auth()

    client = TestClient(app)
    d = datetime(2025, 8, 27, tzinfo=APP_TZ).date()

    with SessionLocal() as db:
        customer = Customer(name="C1")
        db.add(customer)
        db.flush()
        db.add_all(
            [
                Order(code="O1", type="OUTRIGHT", status="NEW", customer_id=customer.id, delivery_date=None),
                Order(
                    code="O2",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 25, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="O3",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 26, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="O4",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 27, 0, 0, tzinfo=APP_TZ),
                ),
            ]
        )
        db.commit()

    resp = client.get("/orders", params={"date": d.isoformat(), "unassigned": "true", "limit": 500})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {o["code"] for o in data} == {"O1", "O2", "O3", "O4"}

    app.dependency_overrides.clear()


def test_on_hold_backlog_includes_null_and_overdue():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    _override_auth()

    client = TestClient(app)
    d = datetime(2025, 8, 27, tzinfo=APP_TZ).date()

    with SessionLocal() as db:
        customer = Customer(name="C1")
        db.add(customer)
        db.flush()
        db.add_all(
            [
                Order(code="H1", type="OUTRIGHT", status="ON_HOLD", customer_id=customer.id, delivery_date=None),
                Order(
                    code="H2",
                    type="OUTRIGHT",
                    status="ON_HOLD",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 25, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="H3",
                    type="OUTRIGHT",
                    status="ON_HOLD",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 26, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="H4",
                    type="OUTRIGHT",
                    status="ON_HOLD",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 27, 0, 0, tzinfo=APP_TZ),
                ),
            ]
        )
        db.commit()

    resp = client.get("/orders", params={"date": d.isoformat(), "status": "ON_HOLD", "limit": 500})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {o["code"] for o in data} == {"H1", "H2", "H3", "H4"}

    app.dependency_overrides.clear()


def test_date_filter_exact_day_when_not_backlog():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    _override_auth()

    client = TestClient(app)
    d = datetime(2025, 8, 27, tzinfo=APP_TZ).date()

    with SessionLocal() as db:
        customer = Customer(name="C1")
        db.add(customer)
        db.flush()
        db.add_all(
            [
                Order(
                    code="E1",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 27, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="E2",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 27, 0, 0, tzinfo=APP_TZ),
                ),
                Order(
                    code="E3",
                    type="OUTRIGHT",
                    status="NEW",
                    customer_id=customer.id,
                    delivery_date=datetime(2025, 8, 26, 0, 0, tzinfo=APP_TZ),
                ),
            ]
        )
        db.commit()

    resp = client.get("/orders", params={"date": d.isoformat(), "limit": 500})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {o["code"] for o in data} == {"E1", "E2"}

    app.dependency_overrides.clear()

