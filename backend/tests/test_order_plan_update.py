import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Order, Plan
from app.routers.orders import update_order, OrderPatch, PlanPatch


class DummySession:
    def __init__(self, order):
        self._order = order

    def get(self, model, ident):
        return self._order

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_update_plan_monthly_amount_precision():
    order = Order(
        code="ORD1",
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
    plan = Plan(
        order_id=1,
        plan_type="INSTALLMENT",
        months=12,
        monthly_amount=Decimal("100.00"),
        status="ACTIVE",
    )
    order.plan = plan
    order.items = []
    order.payments = []

    db = DummySession(order)
    body = OrderPatch(plan=PlanPatch(monthly_amount=123.45))

    with patch("app.routers.orders.recompute_financials", lambda order: None), \
         patch("app.routers.orders.envelope", lambda x: x), \
         patch("app.routers.orders.OrderOut.model_validate", return_value=order):
        update_order(1, body, db)

    assert isinstance(order.plan.monthly_amount, Decimal)
    assert order.plan.monthly_amount == Decimal("123.45")
