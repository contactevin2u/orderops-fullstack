"""PDF generation utilities using ReportLab.

ReportLab is optional. To avoid import-time crashes when it's absent, we only
import it within the functions that actually render PDFs. Each function raises a
clear error if ReportLab is missing so callers can respond with a helpful
message instead of the application failing to start.
"""

from io import BytesIO

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
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT = "Inter"
        BASE_BOLD = "Inter-Bold"
    except Exception:
        BASE_FONT = "Helvetica"
        BASE_BOLD = "Helvetica-Bold"

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Title"].fontName = BASE_BOLD
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Note", parent=styles["Small"], textColor="#555555"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    elems = []

    brand_color = getattr(getattr(order, "company", None), "brand_color", None) or "#000000"
    logo_path = getattr(settings, "COMPANY_LOGO_PATH", None)
    from reportlab.lib.colors import HexColor
    BAR_H = 18  # points

    def _page_deco(c, d):
        c.saveState()
        c.setFillColor(HexColor(brand_color))
        c.rect(0, d.height + d.topMargin + d.bottomMargin - BAR_H, d.width + d.leftMargin + d.rightMargin, BAR_H, fill=1, stroke=0)
        if logo_path:
            try:
                c.drawImage(logo_path, d.leftMargin, d.height + d.topMargin + d.bottomMargin - BAR_H + 2, height=BAR_H-4, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        c.setFont(BASE_BOLD, 10)
        c.setFillColorRGB(1,1,1)
        c.drawRightString(d.width + d.leftMargin, d.height + d.topMargin + d.bottomMargin - BAR_H + 5, getattr(settings, "COMPANY_NAME", ""))
        c.setFont(BASE_FONT, 9)
        c.setFillColorRGB(0,0,0)
        c.drawRightString(d.width + d.leftMargin, 15, f"Page {d.page}")
        c.restoreState()

    title = "CREDIT NOTE" if float(getattr(order, "total", 0) or 0) < 0 else "INVOICE"
    inv_date = getattr(order, "created_at", None)
    elems += [
        Paragraph(getattr(settings, "COMPANY_NAME", ""), styles["Title"]),
        Paragraph(getattr(settings, "COMPANY_ADDRESS", ""), styles["Small"]),
        Spacer(1, 6),
        Paragraph(f"{title} {getattr(order,'code','')}", styles["Heading2"]),
        Paragraph(f"Issue Date: {getattr(inv_date,'strftime',lambda *_: '')('%Y-%m-%d')}", styles["Normal"]),
        Spacer(1, 8),
    ]
    meta_rows = []
    def add(k, v):
        if v:
            meta_rows.append([Paragraph(k, styles["Small"]), Paragraph(str(v), styles["Right"])])
    add("Due Date", getattr(order, "due_date", None))
    add("PO", getattr(order, "po_number", None))
    add("Ref", getattr(order, "reference", None))
    tax_id = getattr(getattr(order, "company", None), "tax_id", None)
    if tax_id:
        add("Tax ID", tax_id)
    if meta_rows:
        t = Table(meta_rows, colWidths=[40*mm, 60*mm])
        t.setStyle(TableStyle([("ALIGN",(1,0),(-1,-1),"RIGHT")]))
        elems += [t, Spacer(1,8)]

    def block(label, obj):
        lines = [f"<b>{label}</b>", getattr(obj,"name", "") or ""]
        attn = getattr(obj,"attn", None)
        if attn:
            lines.append(f"Attn: {attn}")
        addr = getattr(obj,"address", None)
        if addr:
            lines.append(addr)
        email = getattr(obj,"email", None)
        if email:
            lines.append(email)
        return Paragraph("<br/>".join(lines), styles["Normal"])
    bill = block("Bill To", getattr(order, "customer", None) or type("X",(),{})())
    ship_to = getattr(order, "shipping_to", None)
    bill_ship = [ [bill, block("Ship To", ship_to)] ] if ship_to else [ [bill] ]
    bt = Table(bill_ship, colWidths=[90*mm, 90*mm] if ship_to else [180*mm])
    bt.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,colors.grey), ("INNERGRID",(0,0),(-1,-1),0.5,colors.grey), ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6), ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    elems += [bt, Spacer(1,8)]

    header = ["SKU","Description","Qty","Unit","Unit Price","Disc","Tax","Amount"]
    data = [header]
    for it in getattr(order,"items",[]) or []:
        sku = getattr(it,"sku", "") or ""
        name = getattr(it,"name","") or ""
        note = getattr(it,"note","") or ""
        qty = int(getattr(it,"qty",0) or 0)
        unit = getattr(it,"unit","") or "-"
        unit_price = float(getattr(it,"unit_price",0) or 0)
        disc = getattr(it,"discount_rate", None)
        taxr = getattr(it,"tax_rate", None)
        discounted = unit_price * (1 - (disc or 0))
        amount = discounted * qty
        data.append([
            sku,
            Paragraph(name + (f"<br/><font color='#555555' size='9'>{note}</font>" if note else ""), styles["Normal"]),
            f"{qty}",
            unit,
            f"RM{unit_price:,.2f}",
            (f"{disc*100:.0f}%" if disc else "-"),
            (f"{taxr*100:.0f}%" if taxr else "-"),
            f"RM{amount:,.2f}",
        ])
    colw = [20*mm, 70*mm, 15*mm, 15*mm, 25*mm, 15*mm, 15*mm, 25*mm]
    itab = Table(data, colWidths=colw, repeatRows=1)
    itab.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
        ("FONTNAME",(0,0),(-1,0),BASE_BOLD),
        ("GRID",(0,0),(-1,-1),0.25,colors.grey),
        ("ALIGN",(2,1),(-1,-1),"RIGHT"),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    elems += [itab, Spacer(1,10)]

    def row(k,v): return [Paragraph(k, styles["Normal"]), Paragraph(v, styles["Right"])]
    def money(x): return f"RM{float(x or 0):,.2f}"
    subtotal = getattr(order,"subtotal", None)
    tax_total = getattr(order,"tax_total", None)
    shipping = getattr(order,"delivery_fee", None)
    other = getattr(order,"other_fee", None)
    rounding = getattr(order,"rounding", None)
    deposit = getattr(order,"deposit_paid", None)
    total = getattr(order,"total", None)
    summary = []
    if subtotal is not None: summary.append(row("Subtotal", money(subtotal)))
    if tax_total is not None: summary.append(row("Tax", money(tax_total)))
    if shipping: summary.append(row("Shipping", money(shipping)))
    if other: summary.append(row("Other", money(other)))
    if rounding: summary.append(row("Rounding", money(rounding)))
    if deposit: summary.append(row("Deposit Paid", "-" + money(deposit)))
    if total is not None: summary.append(row("Total", money(total)))
    if summary:
        stab = Table(summary, colWidths=[45*mm, 45*mm], hAlign="RIGHT")
        stab.setStyle(TableStyle([("ALIGN",(1,0),(-1,-1),"RIGHT"), ("LINEABOVE",(0,-1),(-1,-1),0.5,colors.black)]))
        elems.append(KeepTogether([stab, Spacer(1,8)]))

    pay = getattr(order,"company", None) or type("X",(),{})()
    lines = [getattr(pay,"bank_name","") or "", getattr(pay,"bank_account_name","") or "", getattr(pay,"bank_account_no","") or ""]
    p = [ Paragraph("<br/>".join([x for x in lines if x]), styles["Normal"]) ]
    qr = getattr(getattr(order,"payment", None),"qrDataUrl", None)
    if qr:
        try:
            import base64
            img_data = qr.split(",",1)[-1]
            qr_img = Image(BytesIO(base64.b64decode(img_data)), width=40*mm, height=40*mm)
            ptab = Table([[p, qr_img]], colWidths=[90*mm, 40*mm])
        except Exception:
            ptab = Table([[p]], colWidths=[90*mm])
    else:
        ptab = Table([[p]], colWidths=[90*mm])
    ptab.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,colors.grey), ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    elems += [ptab, Spacer(1,12)]

    terms = getattr(getattr(order,"footer", None),"terms", None) or ["Payment due upon receipt.","Goods sold are not returnable except by prior arrangement."]
    note = getattr(getattr(order,"footer", None),"note", None)
    elems.append(Paragraph("<br/>".join(f"• {t}" for t in terms), styles["Small"]))
    if note:
        elems.append(Paragraph(note, styles["Small"]))
    elems.append(PageBreak())
    elems += [Paragraph("Terms & Conditions", styles["Heading2"]), Spacer(1,8), Paragraph("<br/>".join(f"• {t}" for t in terms), styles["Small"])]

    def _canvasmaker(*a, **k):
        from reportlab.pdfgen.canvas import Canvas
        k["pageCompression"] = 0
        return Canvas(*a, **k)

    doc.build(elems, onFirstPage=_page_deco, onLaterPages=_page_deco, canvasmaker=_canvasmaker)
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
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
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
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
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

