import sys
from pathlib import Path
from datetime import datetime, date
from types import SimpleNamespace
from decimal import Decimal

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.plan_math import months_elapsed, calculate_plan_due  # noqa: E402


def test_months_elapsed_rule():
    start = datetime(2024, 1, 15)
    assert months_elapsed(start, datetime(2024, 2, 14)) == 1
    assert months_elapsed(start, datetime(2024, 2, 15)) == 2


def test_calculate_plan_due_caps_to_plan_months():
    order = SimpleNamespace(delivery_date=datetime(2024, 1, 1))
    plan = SimpleNamespace(
        plan_type="INSTALLMENT",
        months=3,
        monthly_amount=Decimal("100"),
        status="ACTIVE",
        order=order,
    )
    due = calculate_plan_due(plan, date(2024, 6, 1))
    assert due == Decimal("300.00")


def test_calculate_plan_due_stops_at_returned_at():
    order = SimpleNamespace(
        delivery_date=datetime(2024, 1, 1), returned_at=datetime(2024, 2, 14)
    )
    plan = SimpleNamespace(
        plan_type="RENTAL", monthly_amount=Decimal("100"), status="ACTIVE", order=order
    )
    due = calculate_plan_due(plan, date(2024, 4, 1))
    assert due == Decimal("200.00")


def test_calculate_plan_due_uses_start_date():
    order = SimpleNamespace(delivery_date=datetime(2024, 1, 1))
    plan = SimpleNamespace(
        plan_type="RENTAL",
        monthly_amount=Decimal("100"),
        status="ACTIVE",
        order=order,
        start_date=date(2024, 2, 1),
    )
    due = calculate_plan_due(plan, date(2024, 3, 1))
    assert due == Decimal("200.00")


def test_calculate_plan_due_terminal_plan_capped():
    order = SimpleNamespace(delivery_date=datetime(2024, 1, 1))
    plan = SimpleNamespace(
        plan_type="RENTAL",
        monthly_amount=Decimal("100"),
        status="CANCELLED",
        order=order,
        months=3,
    )
    due = calculate_plan_due(plan, date(2024, 8, 1))
    assert due == Decimal("300.00")
