from decimal import Decimal

from app.models import Order, OrderItem
from app.services.status_updates import mark_cancelled, mark_returned, apply_buyback


class DummySession:
    def commit(self):
        pass

    def refresh(self, obj):
        pass


def _sample_order():
    order = Order(
        code="TMP1",
        type="OUTRIGHT",
        status="NEW",
        customer_id=1,
        subtotal=Decimal("1000"),
        discount=Decimal("0"),
        delivery_fee=Decimal("0"),
        return_delivery_fee=Decimal("0"),
        penalty_fee=Decimal("0"),
        total=Decimal("1000"),
        paid_amount=Decimal("500"),
        balance=Decimal("500"),
    )
    item = OrderItem(
        name="Bed",
        item_type="OUTRIGHT",
        qty=1,
        unit_price=Decimal("1000"),
        line_total=Decimal("1000"),
    )
    order.items = [item]
    order.payments = []
    return order


def test_mark_returned():
    db = DummySession()
    order = _sample_order()
    mark_returned(db, order)
    assert order.status == "RETURNED"
    assert float(order.balance) == 500.0


def test_mark_cancelled_zero_totals():
    db = DummySession()
    order = _sample_order()
    order.paid_amount = Decimal("0")
    mark_cancelled(db, order, "customer cancelled")
    assert order.status == "CANCELLED"
    assert float(order.total) == 0.0
    assert "VOID" in order.notes


def test_apply_buyback():
    db = DummySession()
    order = _sample_order()
    apply_buyback(db, order, Decimal("100"))
    assert order.status == "RETURNED"
    assert float(order.discount) == 100.0
    assert float(order.balance) == 400.0
