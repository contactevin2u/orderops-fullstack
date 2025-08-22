"""PDF generation utilities using ReportLab.

ReportLab is optional. To avoid import-time crashes when it's absent, we only
import it within the functions that actually render PDFs. Each function raises a
clear error if ReportLab is missing so callers can respond with a helpful
message instead of the application failing to start.
"""

from textwrap import wrap
from io import BytesIO
from datetime import date

from ..core.config import settings
from ..models.order import Order
from ..models.payment import Payment
from ..models.plan import Plan


def _draw_lines(c, x, y, lines, max_width_mm=180, leading=14):
    from reportlab.lib.units import mm  # local import

    width = max_width_mm * mm
    for line in lines:
        for seg in wrap(line, 100):
            c.drawString(x * mm, y * mm, seg)
            y -= leading / 3.0
            y -= leading / 3.0
    return y


def invoice_pdf(order: Order) -> bytes:
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'."
        ) from exc

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x * mm, y * mm, f"INVOICE {order.code}")
    y -= 5
    c.setFont("Helvetica", 10)
    inv_date = getattr(order, "created_at", date.today())
    c.drawString(x * mm, y * mm, f"Invoice Date: {inv_date:%Y-%m-%d}")
    y -= 5

    company = [
        settings.COMPANY_NAME,
        settings.COMPANY_ADDRESS,
        f"Phone: {settings.COMPANY_PHONE}",
        f"Email: {settings.COMPANY_EMAIL}",
    ]
    y = _draw_lines(c, x, y, company)
    y -= 5

    cust = [
        f"Bill To: {order.customer.name}",
        f"Phone: {order.customer.phone or '-'}",
        f"Address: {order.customer.address or '-'}",
    ]
    y = _draw_lines(c, x, y, cust)
    y -= 5

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x * mm, y * mm, "Items:")
    y -= 6
    c.setFont("Helvetica", 10)
    for it in order.items:
        line = f"- {it.name} x{int(it.qty)}  @ RM{float(it.unit_price):.2f}  = RM{float(it.line_total):.2f}"
        c.drawString(x * mm, y * mm, line)
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
        c.drawString(x * mm, y * mm, t)
        y -= 5

    y -= 10
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x * mm, y * mm, "Payment Information:")
    y -= 6
    c.setFont("Helvetica", 10)
    c.drawString(x * mm, y * mm, f"{settings.COMPANY_NAME} - {settings.COMPANY_BANK}")
    y -= 5
    c.drawString(x * mm, y * mm, f"Customer Service: {settings.COMPANY_PHONE}")

    # Footer with tax information
    c.setFont("Helvetica", 8)
    c.drawString(x * mm, 10 * mm, f"{settings.TAX_LABEL}: {settings.TAX_PERCENT}%")

    c.showPage()

    y = 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x * mm, y * mm, "Terms & Conditions")
    y -= 10
    c.setFont("Helvetica", 10)
    terms = [
        "Rentals: Payment is due on the first of each month. Late fees apply after a 7-day grace period.",
        "Installments: Installment plans must be approved prior to delivery. Failure to remit payment by the due date may result in service interruption.",
        "Warranty Coverage: Products include a one-year limited warranty against manufacturing defects. This warranty does not cover damage from misuse or unauthorized modifications.",
        "Returns & Exchanges: Goods must be returned within 14 days in original packaging. Certain items may be non-refundable based on their condition or usage.",
        f"Customer Service: For support, call {settings.COMPANY_PHONE}.",
    ]
    y = _draw_lines(c, x, y, terms, leading=12)

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def receipt_pdf(order: Order, payment: Payment) -> bytes:
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'."
        ) from exc

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x * mm, y * mm, f"RECEIPT for {order.code}")
    y -= 10
    c.setFont("Helvetica", 10)
    lines = [
        settings.COMPANY_NAME,
        settings.COMPANY_ADDRESS,
        f"Phone: {settings.COMPANY_PHONE}",
        f"Email: {settings.COMPANY_EMAIL}",
        f"Customer: {order.customer.name}",
        f"Payment Date: {payment.date}",
        f"Amount: RM{float(payment.amount):.2f}",
        f"Method: {payment.method or '-'} Ref: {payment.reference or '-'}",
        f"Status: {payment.status}",
        f"Bank: {settings.COMPANY_BANK}",
        f"Customer Service: {settings.COMPANY_PHONE}",
    ]
    for t in lines:
        c.drawString(x * mm, y * mm, t)
        y -= 6
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def installment_agreement_pdf(order: Order, plan: Plan) -> bytes:
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'."
        ) from exc

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x * mm, y * mm, f"INSTALLMENT AGREEMENT ({order.code})")
    y -= 10
    c.setFont("Helvetica", 10)
    lines = [
        settings.COMPANY_NAME,
        settings.COMPANY_ADDRESS,
        f"Customer: {order.customer.name} ({order.customer.phone or '-'})",
        f"Address: {order.customer.address or '-'}",
        f"Plan: {plan.months} months at RM{float(plan.monthly_amount):.2f}/month (no prorate)",
        "Terms:",
        "- Monthly payments due; no prorate.",
        "- If cancel early, penalty equals remaining unpaid instalments plus return delivery fee.",
        "- Title remains with company until fully paid.",
    ]
    for t in lines:
        c.drawString(x * mm, y * mm, t)
        y -= 6
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf
