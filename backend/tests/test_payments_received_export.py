import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import Base, Payment, Order, Customer  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # SQLite autoincrement works best with Integer
    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Payment.__table__.c.id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[Customer.__table__, Order.__table__, Payment.__table__],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_payments_received_alias_ignores_mark_flag():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    start = date(2024, 1, 1)
    end = date(2024, 1, 31)

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
        db.flush()
        payment = Payment(
            order_id=order.id,
            date=start,
            amount=Decimal("10"),
            method="cash",
            reference="ref",
            category="ORDER",
            status="POSTED",
        )
        db.add(payment)
        db.commit()
        pid = payment.id

    # Without mark parameter
    resp = client.get(f"/export/payments_received.xlsx?start={start}&end={end}")
    assert resp.status_code == 200

    # With mark=true - should still succeed and not mark payment
    resp = client.get(f"/export/payments_received.xlsx?start={start}&end={end}&mark=true")
    assert resp.status_code == 200

    with SessionLocal() as db:
        p = db.get(Payment, pid)
        assert p.exported_at is None

    app.dependency_overrides.clear()
