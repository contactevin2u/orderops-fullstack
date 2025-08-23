from decimal import Decimal

from decimal import Decimal

from app.models import Order, OrderItem
from app.services.status_updates import mark_cancelled, mark_returned, apply_buyback


class DummySession:
    def __init__(self):
        self.added = []
        self.next_id = 1

    def add(self, obj):
        if isinstance(obj, Order):
            if getattr(obj, "id", None) is None:
                obj.id = self.next_id
                self.next_id += 1
        elif isinstance(obj, OrderItem):
            parent = next(
                (o for o in self.added if isinstance(o, Order) and o.id == obj.order_id),
                None,
            )
            if parent:
                parent.items.append(obj)
        elif hasattr(obj, "order_id"):
            parent = next(
                (o for o in self.added if isinstance(o, Order) and o.id == obj.order_id),
                None,
            )
            if parent and hasattr(parent, "payments"):
                parent.payments.append(obj)
        self.added.append(obj)

    def flush(self):
        pass

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


def test_mark_returned_creates_adjustment():
    db = DummySession()
    order = _sample_order()
    mark_returned(db, order)
    assert order.status == "RETURNED"
    assert any(getattr(o, "code", "").endswith("-R") for o in db.added if isinstance(o, Order))


def test_mark_cancelled_creates_adjustment():
    db = DummySession()
    order = _sample_order()
    mark_cancelled(db, order, "customer cancelled")
    assert order.status == "CANCELLED"
    assert any(getattr(o, "code", "").endswith("-I") for o in db.added if isinstance(o, Order))
    assert "VOID" in order.notes


def test_apply_buyback_creates_adjustment_with_discount():
    db = DummySession()
    order = _sample_order()
    apply_buyback(db, order, Decimal("100"), {"type": "percent", "value": Decimal("10")})
    assert order.status == "RETURNED"
    adj = next(o for o in db.added if isinstance(o, Order) and o.code.endswith("-I"))
    assert adj.status == "RETURNED"
    line = adj.items[0]
    assert float(line.line_total) == -90.0
    # Payment recorded
    pay = next(p for p in db.added if hasattr(p, "category") and p.category == "BUYBACK")
    assert float(pay.amount) == -90.0
    assert order.paid_amount == Decimal("410")
