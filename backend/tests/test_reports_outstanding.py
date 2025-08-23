import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
import types

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub out firebase_admin to avoid needing the dependency
fake_admin = types.ModuleType("firebase_admin")
fake_admin.auth = types.ModuleType("firebase_admin.auth")
fake_admin.credentials = types.ModuleType("firebase_admin.credentials")
fake_admin.initialize_app = lambda *a, **kw: None
fake_admin.auth.verify_id_token = lambda *a, **kw: {}
fake_admin.credentials.Certificate = lambda data: data
sys.modules["firebase_admin"] = fake_admin
sys.modules["firebase_admin.auth"] = fake_admin.auth
sys.modules["firebase_admin.credentials"] = fake_admin.credentials

from app.main import app  # noqa: E402
from app.db import get_session  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    Customer,
    Order,
    OrderItem,
    Payment,
    Plan,
)


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import Integer

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.create_function("DATE_PART", 2, lambda part, diff: 0)
        dbapi_connection.create_function(
            "least",
            2,
            lambda a, b: b if a is None else a if b is None else min(a, b),
        )

    Customer.__table__.c.id.type = Integer()
    Order.__table__.c.id.type = Integer()
    Order.__table__.c.customer_id.type = Integer()
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
            OrderItem.__table__,
            Payment.__table__,
            Plan.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_outstanding_includes_cancelled_with_penalty():
    SessionLocal = _setup_db()

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    with SessionLocal() as db:
        cust = Customer(name="C")
        db.add(cust)
        db.flush()
        order = Order(
            code="O1",
            type="OUTRIGHT",
            status="CANCELLED",
            customer_id=cust.id,
            delivery_date=date.today() - timedelta(days=1),
            subtotal=Decimal("100"),
            discount=Decimal("0"),
            delivery_fee=Decimal("0"),
            return_delivery_fee=Decimal("3"),
            penalty_fee=Decimal("5"),
            total=Decimal("100"),
            paid_amount=Decimal("0"),
            balance=Decimal("100"),
        )
        db.add(order)
        db.flush()
        item = OrderItem(
            order_id=order.id,
            name="Bed",
            item_type="OUTRIGHT",
            qty=1,
            unit_price=Decimal("100"),
            line_total=Decimal("100"),
        )
        db.add(item)
        db.commit()

    resp = client.get("/reports/outstanding")
    assert resp.status_code == 200
    data = resp.json()
    assert any(it["code"] == "O1" and it["status"] == "CANCELLED" for it in data["items"])
    found = next(it for it in data["items"] if it["code"] == "O1")
    assert Decimal(str(found["balance"])) == Decimal("8")

    app.dependency_overrides.clear()

