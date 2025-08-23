import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Order, Customer, IdempotentRequest, Plan  # noqa: E402
from app.routers import orders as orders_router  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from sqlalchemy import Integer

    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    IdempotentRequest.__table__.c.id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            IdempotentRequest.__table__,
            Plan.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_return_no_body():
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
            status="DELIVERED",
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

    def fake_mark_returned(db, order, return_date, return_delivery_fee, collect, method, reference, payment_date):
        assert return_date is None
        assert return_delivery_fee is None
        assert collect is False
        assert method is None
        assert reference is None
        assert payment_date is None
        order.status = "RETURNED"
        return order

    def fake_model_validate(order):
        return {"order_id": order.id, "status": order.status}

    headers = {"Idempotency-Key": "abc"}
    with patch.object(orders_router, "mark_returned", fake_mark_returned), \
         patch("app.routers.orders.OrderOut.model_validate", side_effect=fake_model_validate):
        resp = client.post(f"/orders/{oid}/return", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "RETURNED"

    app.dependency_overrides.clear()
