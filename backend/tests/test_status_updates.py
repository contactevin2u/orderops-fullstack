from datetime import date
from decimal import Decimal

import pytest

from app.models import Order, OrderItem, Plan
from app.services.status_updates import (
    mark_cancelled,
    mark_returned,
    apply_buyback,
    cancel_installment,
)


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
                (
                    o
                    for o in self.added
                    if isinstance(o, Order) and o.id == obj.order_id
                ),
                None,
            )
            if parent:
                parent.items.append(obj)
        elif hasattr(obj, "order_id"):
            parent = next(
                (
                    o
                    for o in self.added
                    if isinstance(o, Order) and o.id == obj.order_id
                ),
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


def _rental_order():
    order = Order(
        code="TMP2",
        type="RENTAL",
        status="NEW",
        customer_id=1,
        subtotal=Decimal("100"),
        discount=Decimal("0"),
        delivery_fee=Decimal("0"),
        return_delivery_fee=Decimal("0"),
        penalty_fee=Decimal("0"),
        total=Decimal("100"),
        paid_amount=Decimal("0"),
        balance=Decimal("100"),
    )
    item = OrderItem(
        name="Rental Bed",
        item_type="RENTAL",
        qty=1,
        unit_price=Decimal("100"),
        line_total=Decimal("100"),
    )
    order.items = [item]
    order.payments = []
    order.plan = Plan(
        order_id=0, plan_type="RENTAL", monthly_amount=Decimal("100"), status="ACTIVE"
    )
    return order


def _installment_order():
    order = _sample_order()
    order.type = "INSTALLMENT"
    order.items[0].item_type = "INSTALLMENT"
    order.plan = Plan(
        order_id=0,
        plan_type="INSTALLMENT",
        months=Decimal("12"),
        monthly_amount=Decimal("100"),
        status="ACTIVE",
    )
    return order


def test_mark_returned_creates_adjustment():
    db = DummySession()
    order = _sample_order()
    mark_returned(db, order)
    assert order.status == "RETURNED"
    assert any(
        getattr(o, "code", "").endswith("-R") for o in db.added if isinstance(o, Order)
    )


def test_mark_cancelled_creates_adjustment():
    db = DummySession()
    order = _sample_order()
    mark_cancelled(db, order, "customer cancelled")
    assert order.status == "CANCELLED"
    assert any(
        getattr(o, "code", "").endswith("-I") for o in db.added if isinstance(o, Order)
    )
    assert "VOID" in order.notes


def test_apply_buyback_creates_adjustment_with_discount():
    db = DummySession()
    order = _sample_order()
    apply_buyback(
        db, order, Decimal("100"), {"type": "percent", "value": Decimal("10")}
    )
    assert order.status == "RETURNED"
    adj = next(o for o in db.added if isinstance(o, Order) and o.code.endswith("-I"))
    assert adj.status == "RETURNED"
    line = adj.items[0]
    assert float(line.line_total) == -90.0
    # Payment recorded
    pay = next(
        p for p in db.added if hasattr(p, "category") and p.category == "BUYBACK"
    )
    assert float(pay.amount) == -90.0
    assert order.paid_amount == Decimal("410")


def test_mark_returned_collects_fee_payment():
    db = DummySession()
    order = _sample_order()
    order.return_delivery_fee = Decimal("10")
    mark_returned(
        db,
        order,
        collect=True,
        method="cash",
        reference="r1",
        payment_date=date.today(),
    )
    adj = next(o for o in db.added if isinstance(o, Order) and o.code.endswith("-R"))
    payment = next(p for p in db.added if getattr(p, "category", "") == "DELIVERY")
    assert payment.order_id == adj.id
    assert float(payment.amount) == 10.0
    assert order.paid_amount == Decimal("500")
    assert order.return_delivery_fee == Decimal("0")


def test_cancel_installment_collects_both_payments():
    db = DummySession()
    order = _installment_order()
    cancel_installment(
        db,
        order,
        penalty=Decimal("5"),
        return_fee=Decimal("3"),
        collect=True,
        method="cash",
        reference="r2",
        payment_date=date.today(),
    )
    pays = [p for p in db.added if getattr(p, "category", None)]
    assert any(p.category == "PENALTY" and float(p.amount) == 5.0 for p in pays)
    assert any(p.category == "DELIVERY" and float(p.amount) == 3.0 for p in pays)
    assert order.paid_amount == Decimal("508")
    assert order.balance == Decimal("0")
    assert order.status == "CANCELLED"


def test_cancel_installment_leaves_charges_when_uncollected():
    db = DummySession()
    order = _installment_order()
    cancel_installment(
        db,
        order,
        penalty=Decimal("5"),
        return_fee=Decimal("3"),
        collect=False,
    )
    assert order.balance == Decimal("8")
    assert order.paid_amount == Decimal("500")
    assert order.status == "CANCELLED"


def test_apply_buyback_only_allowed_for_outright():
    db = DummySession()
    order = _rental_order()
    with pytest.raises(ValueError):
        apply_buyback(db, order, Decimal("10"))


def test_rental_return_cancels_plan():
    db = DummySession()
    order = _rental_order()
    mark_returned(db, order)
    assert order.status == "RETURNED"
    assert order.plan.status == "CANCELLED"
    assert any(
        getattr(o, "code", "").endswith("-R") for o in db.added if isinstance(o, Order)
    )
