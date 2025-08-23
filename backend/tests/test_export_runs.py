from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    Payment,
    Order,
    Customer,
    OrderItem,
    Plan,
)
from app.services.status_updates import apply_buyback  # noqa: E402


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Payment.__table__.c.id.type = Integer()
    OrderItem.__table__.c.id.type = Integer()
    OrderItem.__table__.c.order_id.type = Integer()
    Plan.__table__.c.id.type = Integer()
    Plan.__table__.c.order_id.type = Integer()
    Base.metadata.create_all(
        engine,
        tables=[
            Customer.__table__,
            Order.__table__,
            Payment.__table__,
            OrderItem.__table__,
            Plan.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_export_run_and_rollback():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    today = date.today()

    with SessionLocal() as db:
        cust = Customer(name="Test")
        db.add(cust)
        db.flush()
        # Order with positive payment 10
        o1 = Order(
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
        db.add(o1)
        db.flush()
        p1 = Payment(order_id=o1.id, date=today, amount=Decimal("10"), status="POSTED")
        db.add(p1)

        # Order with positive payment 20
        o2 = Order(
            code="O2",
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
        db.add(o2)
        db.flush()
        p2 = Payment(order_id=o2.id, date=today, amount=Decimal("20"), status="POSTED")
        db.add(p2)

        # Order for buyback negative payment -5
        o3 = Order(
            code="O3",
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
        o3.items = []
        o3.payments = []
        db.add(o3)
        db.flush()
        apply_buyback(db, o3, Decimal("5"))  # creates negative payment

        db.commit()

    # Mark export run
    resp = client.post(
        "/export/cash",
        json={"start": str(today), "end": str(today), "mark": True},
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3

    # Listing runs
    runs = client.get("/export/runs").json()
    assert len(runs) == 1
    run = runs[0]
    assert run["count"] == 3
    assert abs(run["sum_amount"] - 25.0) < 0.01
    run_id = run["run_id"]

    # Run details should include negative payment
    details = client.get(f"/export/runs/{run_id}").json()
    assert any(d["amount"] < 0 for d in details)

    # Re-marking same window should return zero rows
    resp2 = client.post(
        "/export/cash",
        json={"start": str(today), "end": str(today), "mark": True},
    )
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 0

    # Rollback and ensure payments eligible again
    rb = client.post(f"/export/runs/{run_id}/rollback")
    assert rb.status_code == 200

    resp3 = client.post(
        "/export/cash",
        json={"start": str(today), "end": str(today), "mark": True},
    )
    assert resp3.status_code == 200
    assert len(resp3.json()["items"]) == 3

    app.dependency_overrides.clear()

