import sys
from pathlib import Path
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Order, Customer, IdempotentRequest, Plan, Payment, OrderItem, Trip  # noqa: E402
from app.routers import orders as orders_router  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from sqlalchemy import Integer

    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    IdempotentRequest.__table__.c.id.type = Integer()
    Payment.__table__.c.id.type = Integer()
    Payment.__table__.c.order_id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Plan.__table__.c.order_id.type = Integer()
    OrderItem.__table__.c.id.type = Integer()
    OrderItem.__table__.c.order_id.type = Integer()
    Trip.__table__.c.id.type = Integer()
    Trip.__table__.c.order_id.type = Integer()
    Trip.__table__.c.driver_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            IdempotentRequest.__table__,
            Plan.__table__,
            Payment.__table__,
            OrderItem.__table__,
            Trip.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_void_idempotency():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="Test")
        db.add(cust)
        db.flush()
        order = Order(
            code="ORD1",
            type="OUTRIGHT",
            status="NEW",
            customer_id=cust.id,
            subtotal=Decimal("0"),
            discount=Decimal("0"),
            delivery_fee=Decimal("0"),
            return_delivery_fee=Decimal("0"),
            penalty_fee=Decimal("0"),
            total=Decimal("0"),
            paid_amount=Decimal("0"),
            balance=Decimal("0"),
        )
        db.add(order)
        db.commit()
        oid = order.id

    # Simplify mark_cancelled to avoid adjustment DB writes
    def fake_mark(db, order, reason):
        order.status = "CANCELLED"
        return order

    orders_router.mark_cancelled = fake_mark

    headers = {"Idempotency-Key": "abc"}
    resp1 = client.post(f"/orders/{oid}/void", headers=headers)
    assert resp1.status_code == 200
    resp2 = client.post(f"/orders/{oid}/void", headers=headers)
    assert resp2.status_code == 200

    with SessionLocal() as db:
        keys = db.query(IdempotentRequest).all()
        assert len(keys) == 1

    app.dependency_overrides.clear()


def test_payment_idempotency():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="C1")
        db.add(cust)
        db.flush()
        order = Order(
            code="O1",
            type="OUTRIGHT",
            status="NEW",
            customer_id=cust.id,
            subtotal=Decimal("0"),
            discount=Decimal("0"),
            delivery_fee=Decimal("0"),
            return_delivery_fee=Decimal("0"),
            penalty_fee=Decimal("0"),
            total=Decimal("0"),
            paid_amount=Decimal("0"),
            balance=Decimal("0"),
        )
        db.add(order)
        db.commit()
        oid = order.id

    headers = {"Idempotency-Key": "paykey"}
    payload = {"order_id": oid, "amount": 10}
    resp1 = client.post("/payments", json=payload, headers=headers)
    assert resp1.status_code == 201
    resp2 = client.post("/payments", json=payload, headers=headers)
    assert resp2.status_code in (200, 201)

    with SessionLocal() as db:
        pays = db.query(Payment).filter_by(order_id=oid).all()
        assert len(pays) == 1

    app.dependency_overrides.clear()
