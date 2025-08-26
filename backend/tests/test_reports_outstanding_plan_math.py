import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
import types

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub firebase_admin
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
from app.models import Customer, Order, OrderItem, Plan  # noqa: E402
from tests.test_reports_outstanding import _setup_db  # noqa: E402

def test_reports_outstanding_plan_math():
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
            code="R1",
            type="RENTAL",
            status="ACTIVE",
            customer_id=cust.id,
            delivery_date=date.today() - timedelta(days=60),
            subtotal=Decimal("0"),
            discount=Decimal("0"),
            delivery_fee=Decimal("10"),
            return_delivery_fee=Decimal("0"),
            penalty_fee=Decimal("0"),
            total=Decimal("0"),
            paid_amount=Decimal("0"),
            balance=Decimal("0"),
        )
        db.add(order)
        db.flush()
        item = OrderItem(
            order_id=order.id,
            name="Rental",
            item_type="RENTAL",
            qty=1,
            unit_price=Decimal("999"),
            line_total=Decimal("999"),
        )
        db.add(item)
        plan = Plan(
            order_id=order.id,
            plan_type="RENTAL",
            start_date=date.today() - timedelta(days=60),
            monthly_amount=Decimal("200"),
            status="ACTIVE",
        )
        db.add(plan)
        db.commit()

    resp = client.get("/reports/outstanding", params={"type": "RENTAL"})
    app.dependency_overrides.clear()
    data = resp.json()
    found = next(it for it in data["items"] if it["code"] == "R1")
    assert Decimal(str(found["expected"])) == Decimal("410")
