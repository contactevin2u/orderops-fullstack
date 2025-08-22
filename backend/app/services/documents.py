"""PDF generation utilities using ReportLab.

This module generates various PDF documents related to orders. ReportLab is an
optional dependency, so we provide a clear error message if it's missing at
runtime.
"""

try:  # pragma: no cover - exercised indirectly in tests
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover - tested by import
    raise ImportError(
        "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'."
    ) from exc

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from textwrap import wrap
from io import BytesIO

from ..core.config import settings
from ..models.order import Order
from ..models.payment import Payment
from ..models.plan import Plan

def _draw_lines(c, x, y, lines, max_width_mm=180, leading=14):
    width = max_width_mm * mm
    for line in lines:
        # wrap if too long (approx by chars)
        for seg in wrap(line, 100):
            c.drawString(x*mm, y*mm, seg)
            y -= leading/3.0
            y -= leading/3.0
    return y

def invoice_pdf(order: Order) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x*mm, y*mm, f"INVOICE {order.code}")
    y -= 10

    c.setFont("Helvetica", 10)
    company = [settings.COMPANY_NAME, settings.COMPANY_ADDRESS, f"Phone: {settings.COMPANY_PHONE}", f"Email: {settings.COMPANY_EMAIL}"]
    y = _draw_lines(c, x, y, company)
    y -= 5

    cust = [f"Bill To: {order.customer.name}", f"Phone: {order.customer.phone or '-'}", f"Address: {order.customer.address or '-'}"]
    y = _draw_lines(c, x, y, cust)
    y -= 5

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x*mm, y*mm, "Items:")
    y -= 6
    c.setFont("Helvetica", 10)
    for it in order.items:
        line = f"- {it.name} x{int(it.qty)}  @ RM{float(it.unit_price):.2f}  = RM{float(it.line_total):.2f}"
        c.drawString(x*mm, y*mm, line)
        y -= 5

    y -= 3
    totals = [
        f"Subtotal: RM{float(order.subtotal):.2f}",
        f"Discount: RM{float(order.discount):.2f}",
        f"Delivery Fee: RM{float(order.delivery_fee):.2f}",
        f"Return Delivery Fee: RM{float(order.return_delivery_fee):.2f}",
        f"Penalty Fee: RM{float(order.penalty_fee):.2f}",
        f"TOTAL: RM{float(order.total):.2f}",
        f"Paid: RM{float(order.paid_amount):.2f}",
        f"Balance: RM{float(order.balance):.2f}",
    ]
    for t in totals:
        c.drawString(x*mm, y*mm, t); y -= 5

    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()
    return pdf

def receipt_pdf(order: Order, payment: Payment) -> bytes:
    buf = BytesIO(); c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x*mm, y*mm, f"RECEIPT for {order.code}")
    y -= 10
    c.setFont("Helvetica", 10)
    lines = [
        settings.COMPANY_NAME, settings.COMPANY_ADDRESS,
        f"Phone: {settings.COMPANY_PHONE}", f"Email: {settings.COMPANY_EMAIL}",
        f"Customer: {order.customer.name}",
        f"Payment Date: {payment.date}",
        f"Amount: RM{float(payment.amount):.2f}",
        f"Method: {payment.method or '-'} Ref: {payment.reference or '-'}",
        f"Status: {payment.status}"
    ]
    for t in lines:
        c.drawString(x*mm, y*mm, t); y -= 6
    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()
    return pdf

def installment_agreement_pdf(order: Order, plan: Plan) -> bytes:
    buf = BytesIO(); c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x*mm, y*mm, f"INSTALLMENT AGREEMENT ({order.code})")
    y -= 10
    c.setFont("Helvetica", 10)
    lines = [
        settings.COMPANY_NAME, settings.COMPANY_ADDRESS,
        f"Customer: {order.customer.name} ({order.customer.phone or '-'})",
        f"Address: {order.customer.address or '-'}",
        f"Plan: {plan.months} months at RM{float(plan.monthly_amount):.2f}/month (no prorate)",
        "Terms:",
        "- Monthly payments due; no prorate.",
        "- If cancel early, penalty equals remaining unpaid instalments plus return delivery fee.",
        "- Title remains with company until fully paid."
    ]
    for t in lines:
        c.drawString(x*mm, y*mm, t); y -= 6
    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()
    return pdf
