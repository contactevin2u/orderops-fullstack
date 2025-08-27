import os
import sys
from pathlib import Path
from datetime import date
from types import SimpleNamespace
from io import BytesIO

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.documents import (
    invoice_pdf,
    receipt_pdf,
    installment_agreement_pdf,
)  # noqa: E402


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


def test_invoice_pdf_bytes():
    order = _sample_order()
    os.environ["USE_HTML_TEMPLATE_INVOICE"] = "1"
    pdf = invoice_pdf(order)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf.startswith(b"%PDF")


def test_credit_note_title():
    order = _sample_order()
    order.total = -5.0
    os.environ["USE_HTML_TEMPLATE_INVOICE"] = "1"
    pdf = invoice_pdf(order)
    try:
        from pdfminer.high_level import extract_text

        text = extract_text(BytesIO(pdf))
        assert "CREDIT NOTE" in text
    except Exception:
        import pytest

        if sys.platform.startswith("win"):
            pytest.xfail("pdfminer unavailable on Windows")
        else:
            raise


def test_invoice_template_smoke():
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("backend/templates"),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("invoice/invoice.html")
    html = tmpl.render(
        doc_title="INVOICE",
        company={
            "name": "ACME",
            "logo_url": "",
            "reg_no": "",
            "tax_label": "Tax",
            "tax_percent": 0,
            "address_lines": [],
            "phone": "",
            "email": "",
            "bank": {
                "name": "",
                "acct_no": "",
                "beneficiary": "",
                "iban": "",
                "swift": "",
            },
        },
        invoice={"number": "1", "date": "", "due_date": ""},
        bill_to={"name": "John", "address_lines": [], "phone": "", "email": ""},
        ship_to=None,
        items=[],
        summary={
            "subtotal": 0,
            "discount": 0,
            "delivery_fee": 0,
            "penalty_amount": 0,
            "buyback_amount": 0,
            "tax_amount": 0,
            "total": 0,
        },
        notes="",
        qr_url=None,
        rtl=False,
    )
    assert "INVOICE" in html


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
