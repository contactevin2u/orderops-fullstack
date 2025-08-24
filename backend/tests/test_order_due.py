from decimal import Decimal

from datetime import date

from app.models import Order, Plan, Payment
from app.routers.orders import get_order_due


class DummySession:
    def __init__(self, order):
        self.order = order

    def get(self, model, id):  # noqa: D401
        return self.order


def test_get_order_due_for_outright_order():
    order = Order(
        id=1,
        code="ORD1",
        type="OUTRIGHT",
        status="NEW",
        customer_id=1,
        subtotal=Decimal("100.00"),
        discount=Decimal("0.00"),
        delivery_fee=Decimal("5.00"),
        return_delivery_fee=Decimal("0.00"),
        penalty_fee=Decimal("0.00"),
        total=Decimal("105.00"),
        paid_amount=Decimal("40.00"),
        balance=Decimal("65.00"),
    )
    order.payments = [
        Payment(
            order_id=1,
            amount=Decimal("40.00"),
            date=date.today(),
            status="POSTED",
        )
    ]
    db = DummySession(order)
    resp = get_order_due(order_id=1, db=db)
    data = resp["data"]
    assert data["expected"] == 105.0
    assert data["paid"] == 40.0
    assert data["balance"] == 65.0


def test_get_order_due_cancelled_order():
    order = Order(
        id=1,
        code="ORD2",
        type="RENTAL",
        status="CANCELLED",
        customer_id=1,
        subtotal=Decimal("0.00"),
        discount=Decimal("0.00"),
        delivery_fee=Decimal("5.00"),
        return_delivery_fee=Decimal("3.00"),
        penalty_fee=Decimal("2.00"),
        total=Decimal("0.00"),
        paid_amount=Decimal("0.00"),
        balance=Decimal("0.00"),
    )
    plan = Plan(plan_type="RENTAL", monthly_amount=Decimal("100"), status="CANCELLED")
    order.plan = plan
    db = DummySession(order)
    resp = get_order_due(order_id=1, db=db)
    data = resp["data"]
    assert data["expected"] == 10.0
    assert data["paid"] == 0.0
    assert data["balance"] == 10.0


def test_get_order_due_returned_with_refund():
    order = Order(
        id=1,
        code="ORD3",
        type="OUTRIGHT",
        status="RETURNED",
        customer_id=1,
        subtotal=Decimal("100.00"),
        discount=Decimal("0.00"),
        delivery_fee=Decimal("0.00"),
        return_delivery_fee=Decimal("0.00"),
        penalty_fee=Decimal("0.00"),
        total=Decimal("100.00"),
        paid_amount=Decimal("0.00"),
        balance=Decimal("0.00"),
    )
    order.payments = [
        Payment(
            order_id=1,
            amount=Decimal("-100.00"),
            date=date.today(),
            status="POSTED",
        )
    ]
    adj = Order(
        id=2,
        code="ORD3-I",
        type="OUTRIGHT",
        status="RETURNED",
        customer_id=1,
        subtotal=Decimal("-100.00"),
        discount=Decimal("0.00"),
        delivery_fee=Decimal("0.00"),
        return_delivery_fee=Decimal("0.00"),
        penalty_fee=Decimal("0.00"),
        total=Decimal("-100.00"),
        paid_amount=Decimal("0.00"),
        balance=Decimal("0.00"),
    )
    adj.payments = []
    order.adjustments = [adj]
    db = DummySession(order)
    resp = get_order_due(order_id=1, db=db)
    data = resp["data"]
    assert data["expected"] == -100.0
    assert data["paid"] == -100.0
    assert data["balance"] == 0.0
