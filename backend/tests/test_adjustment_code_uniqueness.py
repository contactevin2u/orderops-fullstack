import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Customer, Order  # noqa: E402
from app.services.status_updates import mark_cancelled  # noqa: E402
from tests.test_reports_outstanding import _setup_db  # noqa: E402


def test_adjustment_code_uniqueness():
    SessionLocal = _setup_db()
    with SessionLocal() as db:
        cust = Customer(name="C")
        db.add(cust)
        db.flush()
        order = Order(
            code="ORD123",
            type="OUTRIGHT",
            status="NEW",
            customer_id=cust.id,
            delivery_date=date.today(),
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
        db.refresh(order)
        mark_cancelled(db, order, "x")
        mark_cancelled(db, order, "y")
        db.commit()
        codes = [o.code for o in db.query(Order).filter(Order.parent_id == order.id).order_by(Order.id).all()]
        assert codes[0] == "ORD123-C"
        assert codes[1].startswith("ORD123-C-")
