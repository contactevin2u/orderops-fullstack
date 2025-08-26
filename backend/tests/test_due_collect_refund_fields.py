import sys
from pathlib import Path
from decimal import Decimal

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Order, OrderItem, Payment  # noqa: E402
from app.services.status_updates import apply_buyback  # noqa: E402
from app.routers.orders import get_order_due  # noqa: E402


class DummySession:
    def __init__(self, order):
        self.order = order
        self.added = [order]
        self.next_id = 2
        order.items = getattr(order, "items", [])
        order.payments = getattr(order, "payments", [])
        order.adjustments = getattr(order, "adjustments", [])

    def add(self, obj):
        if isinstance(obj, Order):
            if getattr(obj, "id", None) is None:
                obj.id = self.next_id
                self.next_id += 1
            if obj.parent_id == self.order.id:
                self.order.adjustments.append(obj)
        elif isinstance(obj, OrderItem):
            parent = self.order if obj.order_id == self.order.id else next(
                (a for a in self.order.adjustments if a.id == obj.order_id), None
            )
            if parent is not None:
                parent.items = getattr(parent, "items", [])
                parent.items.append(obj)
        elif hasattr(obj, "order_id"):
            parent = self.order if obj.order_id == self.order.id else next(
                (a for a in self.order.adjustments if a.id == obj.order_id), None
            )
            if parent is not None:
                parent.payments = getattr(parent, "payments", [])
                parent.payments.append(obj)
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def get(self, model, id):
        return self.order if id == self.order.id else None

    def execute(self, *args, **kwargs):
        class R:
            def first(self_inner):
                return None
        return R()


def test_due_collect_refund_fields():
    order = Order(
        id=1,
        code="B1",
        type="OUTRIGHT",
        status="NEW",
        customer_id=1,
        subtotal=Decimal("100"),
        discount=Decimal("0"),
        delivery_fee=Decimal("0"),
        return_delivery_fee=Decimal("0"),
        penalty_fee=Decimal("0"),
        total=Decimal("100"),
        paid_amount=Decimal("100"),
        balance=Decimal("0"),
    )
    item = OrderItem(
        order_id=1,
        name="Bed",
        item_type="OUTRIGHT",
        qty=1,
        unit_price=Decimal("100"),
        line_total=Decimal("100"),
    )
    order.items = [item]
    order.payments = [Payment(order_id=1, amount=Decimal("100"), status="POSTED")]
    db = DummySession(order)

    apply_buyback(db, order, Decimal("80"))

    resp = get_order_due(order_id=1, db=db)
    data = resp["data"]
    assert data["to_refund"] > 0
    assert data["to_collect"] == 0
    assert data["balance"] < 0
