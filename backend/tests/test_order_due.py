from decimal import Decimal

from app.models import Order
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
    db = DummySession(order)
    resp = get_order_due(order_id=1, db=db)
    data = resp["data"]
    assert data["expected"] == 105.0
    assert data["paid"] == 40.0
    assert data["balance"] == 65.0
