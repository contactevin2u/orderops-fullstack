"""Utilities to build invoice PDFs using ReportLab."""
from __future__ import annotations

from io import BytesIO

import httpx
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

LOGO_URL = (
    "https://static.wixstatic.com/media/20c5f7_f890d2de838e43ccb1b30e72b247f0b2~mv2.png"
)
QR_URL = (
    "https://static.wixstatic.com/media/20c5f7_98a9fa77aba04052833d15b05fadbe30~mv2.png"
)


async def _fetch_image(url: str) -> BytesIO:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return BytesIO(resp.content)


def _fmt_currency(val: float) -> str:
    return f"{val:,.2f}"


def _fmt(val: str | None) -> str:
    return val if val else "-"


async def build_invoice_pdf(inv: dict) -> bytes:
    """Build and return the invoice PDF as bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title = ParagraphStyle("title", parent=styles["Title"], alignment=1)
    right = ParagraphStyle("right", parent=normal, alignment=2)
    bold = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")

    story: list = []

    # Header with logo and company details
    logo_img = Image(await _fetch_image(LOGO_URL), width=60 * mm, preserveAspectRatio=True)
    company_lines = [
        Paragraph("AA Alive Sdn Bhd", right),
        Paragraph("10 Jalan Perusahaan Amari,", right),
        Paragraph("Batu Caves, 68100 Selangor", right),
        Paragraph("Malaysia", right),
        Paragraph(
            "PS-G-2, Block Pelangi Sentral, Petaling Jaya, Selangor", right
        ),
        Spacer(1, 2),
        Paragraph(
            "+601128686592 | contact@evin2u.com | katil-hospital.my", right
        ),
    ]
    header = Table(
        [[logo_img, KeepTogether(company_lines)]],
        colWidths=[60 * mm, doc.width - 60 * mm],
        style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")],
    )
    story.append(header)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("INVOICE", title))
    story.append(Spacer(1, 4 * mm))

    # Meta grid
    meta = [
        ["Invoice No", inv["number"], "Invoice Date", inv["date"]],
        [
            "Delivery Date",
            inv["delivery_date"],
            "Due Date",
            _fmt(inv.get("due_date")),
        ],
    ]
    meta_table = Table(
        meta,
        colWidths=[25 * mm, 55 * mm, 25 * mm, 55 * mm],
        style=[
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # Bill To / Ship To blocks
    bill = inv["bill_to"]
    bill_lines = [Paragraph("<b>Bill To</b>", bold), Paragraph(bill["name"], normal)]
    for line in bill.get("address", []):
        bill_lines.append(Paragraph(line, normal))
    if bill.get("phone"):
        bill_lines.append(Paragraph(bill["phone"], normal))
    if bill.get("email"):
        bill_lines.append(Paragraph(bill["email"], normal))

    if inv.get("ship_to"):
        ship = inv["ship_to"]
        ship_lines = [
            Paragraph("<b>Ship To</b>", bold),
            Paragraph(ship["name"], normal),
        ]
        for line in ship.get("address", []):
            ship_lines.append(Paragraph(line, normal))
    else:
        ship_lines = [Paragraph("<b>Ship To</b>", bold), Paragraph("-", normal)]

    addr_table = Table(
        [[KeepTogether(bill_lines), KeepTogether(ship_lines)]],
        colWidths=[doc.width / 2.0, doc.width / 2.0],
        style=[("VALIGN", (0, 0), (-1, -1), "TOP")],
    )
    story.append(addr_table)
    story.append(Spacer(1, 6 * mm))

    # Items table
    items_data = [["#", "Description", "SKU", "Qty", "Unit Price", "Line Total"]]
    subtotal = 0.0
    for idx, item in enumerate(inv.get("items", []), start=1):
        line_total = float(item["qty"]) * float(item["unit_price"])
        subtotal += line_total
        items_data.append(
            [
                str(idx),
                item["description"],
                _fmt(item.get("sku")),
                _fmt_currency(item["qty"]),
                _fmt_currency(item["unit_price"]),
                _fmt_currency(line_total),
            ]
        )
    items_table = Table(
        items_data,
        repeatRows=1,
        colWidths=[10 * mm, None, 25 * mm, 20 * mm, 30 * mm, 30 * mm],
        style=[
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    )
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # Totals
    discount = float(inv.get("discount", 0))
    tax_rate = float(inv.get("tax_rate", 0))
    tax = (subtotal - discount) * tax_rate
    delivery_fee = float(inv.get("delivery_fee", 0))
    grand_total = subtotal - discount + tax + delivery_fee
    amount_paid = float(inv.get("amount_paid", 0))
    balance = grand_total - amount_paid

    totals_data = [
        ["Subtotal", _fmt_currency(subtotal)],
        ["Discount", _fmt_currency(discount)],
        [f"Tax ({tax_rate * 100:.0f}%)", _fmt_currency(tax)],
        ["Delivery Fee", _fmt_currency(delivery_fee)],
        ["Grand Total", _fmt_currency(grand_total)],
        ["Amount Paid", _fmt_currency(amount_paid)],
        ["Balance", _fmt_currency(balance)],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[40 * mm, 30 * mm],
        style=[
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEABOVE", (0, 4), (-1, 4), 0.25, colors.black),
            ("LINEABOVE", (0, 6), (-1, 6), 0.5, colors.black),
        ],
    )
    totals_wrap = Table(
        [[Spacer(1, 0), totals_table]],
        colWidths=[doc.width - 70 * mm, 70 * mm],
        style=[("VALIGN", (0, 0), (-1, -1), "TOP")],
    )
    story.append(totals_wrap)
    story.append(Spacer(1, 6 * mm))

    # Payment box
    qr_img = Image(await _fetch_image(QR_URL), width=40 * mm, height=40 * mm)
    pay_lines = [
        Paragraph("Bank: CIMB", normal),
        Paragraph("Account No: 8011366127", normal),
        Paragraph("Account Name: AA Alive Sdn Bhd", normal),
        Paragraph(f"Use reference: {inv['number']}", normal),
    ]
    payment_table = Table(
        [[KeepTogether(pay_lines), qr_img]],
        colWidths=[doc.width - 45 * mm, 45 * mm],
        style=[
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ],
    )
    story.append(payment_table)
    story.append(Spacer(1, 6 * mm))

    # Optional sections
    if inv.get("notes"):
        story.append(Paragraph("Notes", bold))
        story.append(Paragraph(inv["notes"], normal))
        story.append(Spacer(1, 4 * mm))
    if inv.get("terms"):
        story.append(Paragraph("Terms", bold))
        terms = ListFlowable(
            [ListItem(Paragraph(t, normal)) for t in inv["terms"]],
            bulletType="bullet",
        )
        story.append(terms)
        story.append(Spacer(1, 4 * mm))

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin,
            10 * mm,
            f"Page {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

