"""PDF generation utilities using ReportLab.

ReportLab is optional. To avoid import-time crashes when it's absent, we only
import it within the functions that actually render PDFs. Each function raises a
clear error if ReportLab is missing so callers can respond with a helpful
message instead of the application failing to start.
"""

from io import BytesIO
from datetime import date

from ..core.config import settings
from ..models.order import Order
from ..models.payment import Payment
from ..models.plan import Plan


def invoice_pdf(order: Order) -> bytes:
    """Render an invoice using a Fortune 500 style template."""
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'."
        ) from exc

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    elems: list = []

    title = "CREDIT NOTE" if float(getattr(order, "total", 0)) < 0 else "INVOICE"
    inv_date = getattr(order, "created_at", date.today())

    elems.append(Paragraph(settings.COMPANY_NAME, styles["Title"]))
    elems.append(Paragraph(settings.COMPANY_ADDRESS, styles["Normal"]))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(f"{title} {order.code}", styles["Heading2"]))
    elems.append(Paragraph(f"Invoice Date: {inv_date:%Y-%m-%d}", styles["Normal"]))
    elems.append(Spacer(1, 12))

    elems.append(Paragraph(f"Bill To: {order.customer.name}", styles["Normal"]))
    if order.customer.phone:
        elems.append(Paragraph(f"Phone: {order.customer.phone}", styles["Normal"]))
    if order.customer.address:
        elems.append(Paragraph(order.customer.address, styles["Normal"]))
    elems.append(Spacer(1, 12))

    item_data = [["Item", "Qty", "Unit Price", "Total"]]
    for it in order.items:
        item_data.append(
            [
                it.name,
                str(int(it.qty)),
                f"RM{float(it.unit_price):.2f}",
                f"RM{float(it.line_total):.2f}",
            ]
        )
    item_table = Table(item_data, colWidths=[80 * mm, 20 * mm, 30 * mm, 30 * mm])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    elems.append(item_table)
    elems.append(Spacer(1, 12))

    totals = [
        ("Subtotal", getattr(order, "subtotal", 0)),
        ("Discount", getattr(order, "discount", 0)),
        ("Delivery Fee", getattr(order, "delivery_fee", 0)),
        ("Return Delivery Fee", getattr(order, "return_delivery_fee", 0)),
        ("Penalty Fee", getattr(order, "penalty_fee", 0)),
        ("TOTAL", getattr(order, "total", 0)),
        ("Paid", getattr(order, "paid_amount", 0)),
        ("Balance", getattr(order, "balance", 0)),
    ]
    total_data = [[k, f"RM{float(v):.2f}"] for k, v in totals if float(v or 0)]
    if total_data:
        total_table = Table(total_data, colWidths=[110 * mm, 40 * mm])
        total_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        elems.append(total_table)
        elems.append(Spacer(1, 12))

    elems.append(
        Paragraph(
            f"Payment to {settings.COMPANY_BANK}. Customer Service: {settings.COMPANY_PHONE}",
            styles["Normal"],
        )
    )
    elems.append(Paragraph(f"{settings.TAX_LABEL}: {settings.TAX_PERCENT}%", styles["Normal"]))

    def _canvasmaker(*args, **kwargs):
        kwargs["pageCompression"] = 0
        return Canvas(*args, **kwargs)

    doc.build(elems, canvasmaker=_canvasmaker)
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
