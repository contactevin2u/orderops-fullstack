import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.ordersvc import create_from_parsed
from app.reports.outstanding import compute_expected_for_order
from app.routers.orders import get_order_due, update_order, OrderPatch, PlanPatch
from app.models import Order
from tests.test_reports_outstanding import _setup_db


class DummySession:
    def __init__(self, order: Order):
        self.order = order

    def get(self, model, ident):
        return self.order

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_subtotal_includes_first_month_fee_line():
    SessionLocal = _setup_db()
    with SessionLocal() as db:
        payload = {
            "customer": {"name": "C"},
            "order": {
                "type": "RENTAL",
                "code": "O1",
                "delivery_date": str(date.today()),
                "items": [
                    {
                        "name": "Bed",
                        "item_type": "OUTRIGHT",
                        "qty": 1,
                        "unit_price": 200,
                        "line_total": 200,
                    }
                ],
                "charges": {},
                "plan": {"plan_type": "RENTAL", "monthly_amount": 100},
                "totals": {},
            },
        }
        order = create_from_parsed(db, payload)
        fee_lines = [
            it for it in order.items if it.item_type == "FEE" and it.name.startswith("First Month")
        ]
        assert len(fee_lines) == 1
        assert order.subtotal == Decimal("300.00")
        assert order.total == Decimal("300.00")
        assert order.plan.upfront_billed_amount == Decimal("100.00")


def test_mixed_order_expected_and_due_alignment():
    SessionLocal = _setup_db()
    db = SessionLocal()
    start = date.today() - timedelta(days=60)
    payload = {
        "customer": {"name": "C"},
        "order": {
            "type": "MIXED",
            "code": "O2",
            "delivery_date": str(start),
            "items": [
                {
                    "name": "Bed",
                    "item_type": "OUTRIGHT",
                    "qty": 1,
                    "unit_price": 200,
                    "line_total": 200,
                }
            ],
            "charges": {},
            "plan": {
                "plan_type": "RENTAL",
                "monthly_amount": 100,
                "months": 6,
                "start_date": str(start),
            },
            "totals": {},
        },
    }
    order = create_from_parsed(db, payload)
    order.plan
    order.items
    order.payments
    order.adjustments
    as_of = start + timedelta(days=60)
    resp = get_order_due(order.id, as_of, db=db)
    expected = compute_expected_for_order(order, as_of)
    assert Decimal(str(resp["data"]["expected"])) == expected
    assert Decimal(str(resp["data"]["balance"])) == expected
    db.close()


def test_patch_monthly_amount_updates_fee_line():
    SessionLocal = _setup_db()
    with SessionLocal() as db:
        payload = {
            "customer": {"name": "C"},
            "order": {
                "type": "RENTAL",
                "code": "O3",
                "delivery_date": str(date.today()),
                "items": [],
                "charges": {},
                "plan": {"plan_type": "RENTAL", "monthly_amount": 100},
                "totals": {},
            },
        }
        order = create_from_parsed(db, payload)
        order.plan
        order.items
        order.payments
        order.adjustments
    body = OrderPatch(plan=PlanPatch(monthly_amount=150))
    with patch("app.routers.orders.envelope", lambda x: x), patch(
        "app.routers.orders.OrderOut.model_validate", return_value=order
    ):
        update_order(order.id, body, DummySession(order))

    fee_lines = [
        it for it in order.items if it.item_type == "FEE" and it.name.startswith("First Month")
    ]
    assert len(fee_lines) == 1
    assert fee_lines[0].line_total == Decimal("150.00")
    assert order.plan.upfront_billed_amount == Decimal("150.00")
