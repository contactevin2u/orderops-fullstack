import sys
from pathlib import Path
from decimal import Decimal

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Order, OrderItem, Payment  # noqa: E402
from app.services.ordersvc import recompute_financials  # noqa: E402


def test_recompute_paid_from_ledger():
    order = Order(
        id=1,
        code="O1",
        type="OUTRIGHT",
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
    item = OrderItem(
        order_id=1,
        name="Bed",
        item_type="OUTRIGHT",
        qty=1,
        unit_price=Decimal("200"),
        line_total=Decimal("200"),
    )
    order.items = [item]
    order.payments = [
        Payment(order_id=1, amount=Decimal("100"), status="POSTED"),
        Payment(order_id=1, amount=Decimal("50"), status="POSTED"),
        Payment(order_id=1, amount=Decimal("20"), status="VOIDED"),
    ]

    recompute_financials(order)
    assert order.paid_amount == Decimal("150.00")
    assert order.balance == Decimal("50.00")
