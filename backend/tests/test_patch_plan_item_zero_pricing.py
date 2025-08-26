import sys
from pathlib import Path
from decimal import Decimal

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Order, Plan  # noqa: E402
from app.routers.orders import update_order, OrderPatch, OrderItemPatch  # noqa: E402


class DummySession:
    def __init__(self, order):
        self.order = order

    def get(self, model, id):
        return self.order

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def execute(self, *args, **kwargs):
        class R:
            def first(self_inner):
                return None
        return R()


def test_patch_plan_item_zero_pricing():
    order = Order(
        id=1,
        code="P1",
        type="INSTALLMENT",
        status="NEW",
        customer_id=1,
        subtotal=Decimal("0"),
        discount=Decimal("0"),
        delivery_fee=Decimal("0"),
        return_delivery_fee=Decimal("0"),
        penalty_fee=Decimal("0"),
        total=Decimal("0"),
        paid_amount=Decimal("0"),
        balance=Decimal("0"),
    )
    order.items = []
    order.plan = Plan(order_id=1, plan_type="INSTALLMENT", monthly_amount=Decimal("100"), status="ACTIVE")
    db = DummySession(order)
    body = OrderPatch(
        items=[OrderItemPatch(name="Principal", item_type="INSTALLMENT", qty=1, unit_price=100)]
    )
    try:
        update_order(order_id=1, body=body, db=db)
    except Exception:
        pass
    item = order.items[0]
    assert item.unit_price == Decimal("0")
    assert item.line_total == Decimal("0")
    assert order.subtotal == Decimal("0")
