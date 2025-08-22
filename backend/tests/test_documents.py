import sys
from pathlib import Path
from datetime import date
from types import SimpleNamespace

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.documents import invoice_pdf, receipt_pdf, installment_agreement_pdf  # noqa: E402


def _sample_order():
    customer = SimpleNamespace(name="John Doe", phone="123", address="123 Street")
    item = SimpleNamespace(name="Widget", qty=1, unit_price=10.0, line_total=10.0)
    return SimpleNamespace(
        code="ORD001",
        customer=customer,
        items=[item],
        subtotal=10.0,
        discount=0.0,
        delivery_fee=0.0,
        return_delivery_fee=0.0,
        penalty_fee=0.0,
        total=10.0,
        paid_amount=0.0,
        balance=10.0,
    )


def _sample_payment():
    return SimpleNamespace(
        date=date.today(),
        amount=10.0,
        method="cash",
        reference="ref",
        status="POSTED",
    )


def _sample_plan():
    return SimpleNamespace(months=6, monthly_amount=1.0)


def test_invoice_pdf_generates_bytes():
    order = _sample_order()
    pdf = invoice_pdf(order)
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 0


def test_receipt_pdf_generates_bytes():
    order = _sample_order()
    payment = _sample_payment()
    pdf = receipt_pdf(order, payment)
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 0


def test_installment_agreement_pdf_generates_bytes():
    order = _sample_order()
    plan = _sample_plan()
    pdf = installment_agreement_pdf(order, plan)
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 0
