"""
PDF generation utilities (ReportLab-only).

Renders:
- Invoice / Credit Note (styled ReportLab template with watermark)
- Receipt
- Installment Agreement

No HTML/Jinja/WeasyPrint paths.
Images: prefer local files; fallback to remote URLs with timeout.
SKU & Description cells wrap (CJK wrapping) to avoid overlap.
"""

from io import BytesIO
import os

# Project settings and models
from ..core.config import settings
from ..models.order import Order
from ..models.payment import Payment
from ..models.plan import Plan


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def invoice_pdf(order: Order) -> bytes:
    """Render an invoice (or credit note when total < 0) as a PDF using ReportLab."""
    return _reportlab_invoice_pdf(order)


# ---------------------------------------------------------------------------
# Constants (banking & default image URLs)
# ---------------------------------------------------------------------------

BENEFICIARY_NAME = "AA Alive Sdn. Bhd."
BANK_NAME = "CIMB Bank"
BANK_ACCOUNT_NO = "8011366127"

# Fallback remote images (overridable via settings.*_URL or local *_PATH)
DEFAULT_LOGO_URL = "https://static.wixstatic.com/media/20c5f7_f890d2de838e43ccb1b30e72b247f0b2~mv2.png"
DEFAULT_QR_URL = "https://static.wixstatic.com/media/20c5f7_98a9fa77aba04052833d15b05fadbe30~mv2.png"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fit_colwidths(widths_pts, frame_width_pts: float):
    """Scale a list of widths (points) to fit the available frame width."""
    total = sum(widths_pts)
    if total <= frame_width_pts or total <= 0:
        return widths_pts
    scale = frame_width_pts / float(total)
    return [w * scale for w in widths_pts]


def _file_exists(path: str | None) -> bool:
    try:
        return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _fetch_image_bytes(url: str, timeout: float = 5.0):
    """Fetch a remote image and return raw bytes; None on failure."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _image_reader(local_path: str | None, url: str | None, timeout: float = 5.0):
    """Return a ReportLab ImageReader from a local path or remote URL bytes."""
    try:
        from reportlab.lib.utils import ImageReader
    except Exception:
        return None
    # Prefer local
    if _file_exists(local_path):
        try:
            return ImageReader(local_path)
        except Exception:
            pass
    # Fallback to remote
    if url:
        data = _fetch_image_bytes(url, timeout=timeout)
        if data:
            try:
                return ImageReader(BytesIO(data))
            except Exception:
                pass
    return None


# ---------------------------------------------------------------------------
# Polished ReportLab invoice template
# ---------------------------------------------------------------------------

def _reportlab_invoice_pdf(order: Order) -> bytes:
    """Render an invoice using a polished ReportLab template (styling + images + watermark)."""
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Image,
            KeepTogether,
            PageBreak,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    # --- theme & helpers -----------------------------------------------------
    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
    except Exception:
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    BRAND_COLOR = getattr(getattr(order, "company", None), "brand_color", "#0F172A") or "#0F172A"
    ACCENT_COLOR = getattr(getattr(order, "company", None), "accent_color", "#2563EB") or "#2563EB"
    CURRENCY = getattr(settings, "CURRENCY_PREFIX", "RM") or "RM"

    def money(x):
        try:
            return f"{CURRENCY}{float(x or 0):,.2f}"
        except Exception:
            return f"{CURRENCY}0.00"

    def _fmt_qty(q):
        try:
            qf = float(q or 0)
            s = f"{qf:.2f}".rstrip("0").rstrip(".")
            return s if s else "0"
        except Exception:
            return str(q or 0)

    # Local paths (preferred)
    LOGO_PATH = getattr(settings, "COMPANY_LOGO_PATH", None)
    QR_IMAGE_PATH = getattr(settings, "PAYMENT_QR_IMAGE_PATH", None) or getattr(settings, "COMPANY_QR_IMAGE_PATH", None)

    # Remote URLs (fallback)
    LOGO_URL = getattr(settings, "COMPANY_LOGO_URL", None) or DEFAULT_LOGO_URL
    QR_URL = getattr(settings, "PAYMENT_QR_URL", None) or getattr(settings, "COMPANY_QR_URL", None) or DEFAULT_QR_URL

    # ImageReaders
    logo_reader = _image_reader(LOGO_PATH, LOGO_URL)
    # QR image is used as a Flowable later (we'll feed bytes to Image)
    qr_remote_bytes = None  # lazily fetched if needed

    # --- styles --------------------------------------------------------------
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Title"].fontName = BASE_BOLD

    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Small"], textColor="#555555"))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=14, leading=16))
    styles.add(ParagraphStyle(name="Wrap", parent=styles["Normal"], wordWrap="CJK"))
    styles.add(ParagraphStyle(name="WrapBold", parent=styles["Wrap"], fontName=BASE_BOLD))

    # --- doc & page decoration ----------------------------------------------
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    FRAME_W = doc.width  # available frame width in points

    BAR_H = 18  # header band height (pt)
    company_name = getattr(settings, "COMPANY_NAME", "")

    def _draw_watermark(c, d):
        """Diagonal watermark drawn behind content."""
        text = getattr(order, "status", None)
        text = (str(text).upper() if text else company_name or "INVOICE")
        c.saveState()
        # Very light gray + alpha if available
        try:
            c.setFillColorRGB(0.85, 0.85, 0.85)
            set_alpha = getattr(c, "setFillAlpha", None)
            if set_alpha:
                set_alpha(0.08)
        except Exception:
            pass
        c.translate(d.leftMargin + d.width / 2.0, d.bottomMargin + d.height / 2.0)
        c.rotate(45)
        c.setFont(BASE_BOLD, 90)
        # Centered text
        tw = c.stringWidth(text, BASE_BOLD, 90)
        c.drawString(-tw / 2.0, -20, text)
        c.restoreState()

    def _page_deco(c, d):
        # Watermark first (behind)
        _draw_watermark(c, d)

        c.saveState()
        # Top brand bar
        c.setFillColor(HexColor(BRAND_COLOR))
        c.rect(
            0,
            d.height + d.topMargin + d.bottomMargin - BAR_H,
            d.width + d.leftMargin + d.rightMargin,
            BAR_H,
            fill=1,
            stroke=0,
        )
        # Header logo with explicit sizing
        if logo_reader:
            try:
                iw, ih = logo_reader.getSize()
                target_h = BAR_H - 4
                target_w = (iw / float(ih)) * target_h if ih else target_h
                c.drawImage(
                    logo_reader,
                    d.leftMargin,
                    d.height + d.topMargin + d.bottomMargin - BAR_H + 2,
                    width=target_w,
                    height=target_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
        # Company name (top right)
        c.setFillColor(colors.white)
        c.setFont(BASE_BOLD, 10)
        c.drawRightString(
            d.width + d.leftMargin,
            d.height + d.topMargin + d.bottomMargin - BAR_H + 5,
            company_name,
        )
        # Footer page number
        c.setFont(BASE_FONT, 9)
        c.setFillColor(colors.black)
        c.drawRightString(d.width + d.leftMargin, 15, f"Page {d.page}")
        c.restoreState()

    elems = []

    # --- top block (title + dates)  [NO fragile header tables] ---------------
    title = "CREDIT NOTE" if float(getattr(order, "total", 0) or 0) < 0 else "INVOICE"
    inv_code = getattr(order, "code", "") or ""
    inv_date = getattr(order, "created_at", None)
    due_date = getattr(order, "due_date", None)

    elems.append(Paragraph(f"{title} <font color='{ACCENT_COLOR}'>{inv_code}</font>", styles["H2"]))
    elems.append(
        Paragraph(
            f"Issue Date: {getattr(inv_date, 'strftime', lambda *_:'' )('%Y-%m-%d')}"
            + (f" &nbsp;&nbsp;•&nbsp;&nbsp; Due: {due_date}" if due_date else ""),
            styles["Normal"],
        )
    )
    elems.append(Spacer(1, 6))

    # --- From / Bill To (/ Ship To) in a single boxed table ------------------
    def block(label, name=None, address=None, email=None, phone=None):
        bits = [f"<b>{label}</b>"]
        if name: bits.append(name)
        if address: bits.append(address)
        if email: bits.append(email)
        if phone: bits.append(phone)
        return Paragraph("<br/>".join(bits), styles["Wrap"])

    company_addr = getattr(settings, "COMPANY_ADDRESS", "") or ""
    company_email = getattr(settings, "COMPANY_EMAIL", "") or ""
    company_phone = getattr(settings, "COMPANY_PHONE", "") or ""
    from_block = block("From", company_name, company_addr, company_email, company_phone)

    cust = getattr(order, "customer", None) or type("X", (), {})()
    bill_name = getattr(cust, "name", "") or ""
    bill_addr = getattr(cust, "address", None) or ""
    bill_email = getattr(cust, "email", None) or ""
    bill_phone = getattr(cust, "phone", None) or ""
    bill_block = block("Bill To", bill_name, bill_addr, bill_email, bill_phone)

    ship = getattr(order, "shipping_to", None)
    ship_block = None
    if ship:
        ship_block = block(
            "Ship To",
            getattr(ship, "name", "") or "",
            getattr(ship, "address", None) or "",
            getattr(ship, "email", None) or "",
            getattr(ship, "phone", None) or "",
        )

    from reportlab.lib.units import mm as _mm  # mm->pt

    if ship_block:
        cols_mm = [56, 56, 56]  # ~168mm
        data = [[from_block, bill_block, ship_block]]
    else:
        cols_mm = [85, 85]  # ~170mm
        data = [[from_block, bill_block]]

    bt_cols = _fit_colwidths([v * _mm for v in cols_mm], FRAME_W)
    bt = Table(data, colWidths=bt_cols)
    bt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elems += [bt, Spacer(1, 10)]

    # --- items table (CJK wrapping for SKU & Description) --------------------
    header = ["SKU", "Description", "Qty", "Unit", "Unit Price", "Disc", "Tax", "Amount"]
    data = [header]
    for it in getattr(order, "items", []) or []:
        sku = getattr(it, "sku", "") or ""
        name = getattr(it, "name", "") or ""
        note = getattr(it, "note", "") or ""
        qty = getattr(it, "qty", 0) or 0
        unit = getattr(it, "unit", "") or "-"
        unit_price = float(getattr(it, "unit_price", 0) or 0)
        disc = getattr(it, "discount_rate", None)
        taxr = getattr(it, "tax_rate", None)
        discounted = unit_price * (1 - (disc or 0))
        amount = discounted * float(qty or 0)

        # Use Paragraphs with CJK wrapping to avoid overlap even for long strings
        sku_para = Paragraph(sku, styles["Wrap"])
        desc_text = name + (f"<br/><font color='#6B7280' size='9'>{note}</font>" if note else "")
        desc_para = Paragraph(desc_text, styles["Wrap"])

        data.append([
            sku_para,
            desc_para,
            _fmt_qty(qty),
            unit,
            money(unit_price),
            (f"{disc * 100:.0f}%" if disc else "-"),
            (f"{taxr * 100:.0f}%" if taxr else "-"),
            money(amount),
        ])

    # Give SKU a bit more room, description gets the bulk, ensure totals fit
    raw_cols_mm = [24, 66, 14, 16, 24, 14, 14, 24]  # ~196mm pre-scale; will scale to frame
    itab_cols_pts = [v * _mm for v in raw_cols_mm]
    itab_cols = _fit_colwidths(itab_cols_pts, FRAME_W)

    itab = Table(data, colWidths=itab_cols, repeatRows=1)
    itab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(BRAND_COLOR)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),   # SKU
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems += [itab, Spacer(1, 12)]

    # --- summary -------------------------------------------------------------
    def row(k, v):
        return [Paragraph(k, styles["Wrap"]), Paragraph(v, styles["Right"])]

    subtotal = getattr(order, "subtotal", None)
    discount = getattr(order, "discount", None)
    tax_total = getattr(order, "tax_total", None)
    shipping = getattr(order, "delivery_fee", None)
    return_delivery = getattr(order, "return_delivery_fee", None)
    penalty = getattr(order, "penalty_fee", None)
    other = getattr(order, "other_fee", None)
    rounding = getattr(order, "rounding", None)
    deposit = getattr(order, "deposit_paid", None)
    buyback = getattr(order, "buyback_amount", None)
    total = getattr(order, "total", None)
    tax_label = getattr(getattr(order, "company", None), "tax_label", "Tax") or "Tax"

    summary = []
    if subtotal is not None: summary.append(row("Subtotal", money(subtotal)))
    if discount: summary.append(row("Discount", "-" + money(discount)))
    if shipping: summary.append(row("Delivery Fee", money(shipping)))
    if return_delivery: summary.append(row("Return Delivery", money(return_delivery)))
    if penalty: summary.append(row("Penalty", money(penalty)))
    if other: summary.append(row("Other", money(other)))
    if rounding: summary.append(row("Rounding", money(rounding)))
    if buyback: summary.append(row("Buyback", "-" + money(buyback)))
    if tax_total is not None: summary.append(row(tax_label, money(tax_total)))
    if deposit: summary.append(row("Deposit Paid", "-" + money(deposit)))

    if summary:
        stab = Table(summary, colWidths=_fit_colwidths([60 * mm, 45 * mm], FRAME_W), hAlign="RIGHT")
        stab.setStyle(TableStyle([
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elems.append(KeepTogether([stab, Spacer(1, 6)]))

    if total is not None:
        trow = Table([row("Total", money(total))], colWidths=_fit_colwidths([60 * mm, 45 * mm], FRAME_W), hAlign="RIGHT")
        trow.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1.2, HexColor(ACCENT_COLOR)),
            ("FONTNAME", (0, 0), (-1, -1), BASE_BOLD),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elems.append(KeepTogether([trow, Spacer(1, 10)]))

    # --- payment box with QR (local path, base64 from order, or remote URL) ---
    bank_lines = [
        f"Beneficiary: {BENEFICIARY_NAME}",
        f"Bank: {BANK_NAME}",
        f"Account No.: {BANK_ACCOUNT_NO}",
    ]
    p = [Paragraph("<br/>".join(bank_lines), styles["Normal"])]

    qr_img_flow = None
    # (1) order.payment.qrDataUrl (base64)
    qr_b64 = getattr(getattr(order, "payment", None), "qrDataUrl", None)
    if qr_b64:
        try:
            import base64
            img_data = qr_b64.split(",", 1)[-1]
            qr_img_flow = Image(BytesIO(base64.b64decode(img_data)), width=40 * mm, height=40 * mm)
        except Exception:
            qr_img_flow = None
    # (2) local file
    if qr_img_flow is None and _file_exists(QR_IMAGE_PATH):
        try:
            qr_img_flow = Image(QR_IMAGE_PATH, width=40 * mm, height=40 * mm)
        except Exception:
            qr_img_flow = None
    # (3) remote URL
    if qr_img_flow is None and QR_URL:
        try:
            data = _fetch_image_bytes(QR_URL)
            if data:
                qr_img_flow = Image(BytesIO(data), width=40 * mm, height=40 * mm)
        except Exception:
            qr_img_flow = None

    if qr_img_flow:
        ptab = Table([[p[0], qr_img_flow]], colWidths=_fit_colwidths([100 * mm, 40 * mm], FRAME_W))
    else:
        ptab = Table([[p[0]]], colWidths=_fit_colwidths([100 * mm], FRAME_W))

    ptab.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems += [ptab, Spacer(1, 12)]

    # --- notes & T&C ---------------------------------------------------------
    terms = getattr(getattr(order, "footer", None), "terms", None) or [
        "Payment due upon receipt.",
        "Goods sold are not returnable except by prior arrangement.",
    ]
    note = getattr(getattr(order, "footer", None), "note", None)

    if note:
        elems.append(Paragraph(note, styles["Muted"]))
        elems.append(Spacer(1, 8))

    elems.append(Paragraph("Terms & Conditions", styles["H2"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("<br/>".join(f"• {t}" for t in terms), styles["Small"]))

    # Optional bilingual page (unchanged content)
    elems.append(PageBreak())
    elems.append(Paragraph("Terms & Conditions", styles["H2"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("English – “Terms & Conditions”", styles["Normal"]))
    elems.append(Spacer(1, 4))
    english_terms = [
        ("Payment, Default & Remedies. All amounts are due on or before the due date. If you fail to pay any amount when due, we may, to the maximum extent permitted by law: (a) charge late fees and interest; (b) suspend delivery/service and accelerate all amounts outstanding; (c) report the default to credit reporting agencies, including CTOS Data Systems Sdn Bhd; and (d) assign or sell our receivables (including this invoice) to a third-party collector without further consent."),
        ("Data Processing & Privacy Consent. You consent to our collection, use and disclosure of your personal data for account management, payment recovery, fraud prevention and legal compliance, including disclosure to credit reporting agencies (such as CTOS) and appointed collection partners, until all sums are fully settled, subject to applicable law, including the Personal Data Protection Act 2010."),
        ("Ownership & Repossession (Instalment/Rental). Title to goods remains with the Company until full payment is received (for sales) and at all times during rental. Upon default or termination, we may, as permitted by law, enter the location of the goods with reasonable notice (or without notice if legally allowed) to remove and repossess our assets; you must grant access and cooperation. Associated removal, transport and restoration costs are chargeable to you."),
        ("Damage & Loss (Rental). You are responsible for any loss or damage beyond fair wear and tear. Repair, parts and replacement costs (including logistics and technician time) will be charged. If damage renders the equipment unusable, rental charges may continue during downtime caused by your act/omission."),
        ("Delivery, Risk & Insurance. Risk passes on delivery for sales; for rentals, risk of loss/damage remains with you while equipment is in your care. You agree to take reasonable care and, where applicable, maintain suitable insurance."),
        ("Assignment & Third-Party Collection. We may at any time assign, novate or sell any receivables or this agreement to financiers or collection agencies. Your obligations remain unchanged."),
        ("Limitation of Liability. To the maximum extent permitted by law, we are not liable for indirect, special or consequential losses. Our aggregate liability is capped at the price paid for the goods/services giving rise to the claim."),
        ("Governing Law & Jurisdiction. This agreement is governed by the laws of Malaysia. You submit to the exclusive jurisdiction of the courts of Kuala Lumpur."),
        ("Acceptance. By signing, placing the order, taking delivery, or making any payment, you accept these Terms & Conditions."),
    ]
    for para in english_terms:
        elems.append(Paragraph(para, styles["Small"]))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 8))
    elems.append(Paragraph("Bahasa Melayu – “Terma & Syarat”", styles["Normal"]))
    elems.append(Spacer(1, 4))
    malay_terms = [
        ("Pembayaran, Kegagalan & Pemulihan. Semua amaun perlu dibayar pada atau sebelum tarikh akhir. Jika anda gagal membayar, kami boleh, setakat yang dibenarkan undang-undang: (a) mengenakan caj lewat dan faedah; (b) menggantung penghantaran/perkhidmatan dan mempercepatkan semua amaun tertunggak; (c) melaporkan kegagalan bayaran kepada agensi pelaporan kredit termasuk CTOS Data Systems Sdn Bhd; dan (d) menyerah hak atau menjual terimaan kami (termasuk invois ini) kepada pihak pengutip hutang tanpa keizinan lanjut."),
        ("Pemprosesan Data & Persetujuan Privasi. Anda bersetuju bahawa kami boleh mengumpul, menggunakan dan mendedahkan data peribadi anda bagi tujuan pengurusan akaun, pemulihan bayaran, pencegahan penipuan dan pematuhan undang-undang, termasuk pendedahan kepada agensi pelaporan kredit (seperti CTOS) dan rakan kutipan yang dilantik, sehingga semua amaun diselesaikan sepenuhnya, tertakluk kepada undang-undang yang berkenaan termasuk Akta Perlindungan Data Peribadi 2010."),
        ("Pemilikan & Pengambilan Semula (Ansuran/Sewaan). Hak milik kekal milik Syarikat sehingga bayaran penuh diterima (jualan) dan pada setiap masa sepanjang tempoh sewaan. Jika berlaku kegagalan atau penamatan, kami boleh, seperti yang dibenarkan undang-undang, memasuki lokasi barangan dengan notis munasabah (atau tanpa notis jika dibenarkan undang-undang) untuk mengalih keluar dan mengambil balik aset kami; anda hendaklah memberikan akses dan kerjasama. Kos pengalihan, pengangkutan dan pemulihan adalah ditanggung oleh anda."),
        ("Kerosakan & Kehilangan (Sewaan). Anda bertanggungjawab atas sebarang kerosakan atau kehilangan selain daripada haus dan lusuh biasa. Kos pembaikan, alat ganti dan penggantian (termasuk logistik dan masa juruteknik) akan dicajkan. Jika kerosakan menyebabkan peralatan tidak boleh digunakan, caj sewaan boleh diteruskan sepanjang tempoh henti yang berpunca daripada tindakan/kelalaian anda."),
        ("Penghantaran, Risiko & Insurans. Risiko berpindah semasa penghantaran bagi jualan; bagi sewaan, risiko kehilangan/kerosakan berada pada anda sementara peralatan berada dalam jagaan anda. Anda bersetuju menjaga peralatan dengan sewajarnya dan, jika berkenaan, mengekalkan insurans yang sesuai."),
        ("Penyerahan & Pengutipan Pihak Ketiga. Kami boleh pada bila-bila masa menyerah hak, menovat atau menjual mana-mana terimaan atau perjanjian ini kepada pembiaya atau agensi kutipan. Kewajipan anda tidak berubah."),
        ("Had Tanggungan. Setakat yang dibenarkan undang-undang, kami tidak bertanggungan atas kerugian tidak langsung, khas atau berbangkit. Jumlah tanggungan kami terhad kepada harga yang dibayar bagi barangan/perkhidmatan yang berkaitan."),
        ("Undang-undang Mentadbir & Bidang Kuasa. Terma ini ditadbir oleh undang-undang Malaysia. Anda bersetuju tertakluk kepada bidang kuasa eksklusif Mahkamah Kuala Lumpur."),
        ("Penerimaan. Dengan menandatangani, membuat pesanan, menerima penghantaran, atau membuat sebarang pembayaran, anda bersetuju dengan Terma & Syarat ini."),
    ]
    for para in malay_terms:
        elems.append(Paragraph(para, styles["Small"]))
        elems.append(Spacer(1, 4))

    # build
    def _canvasmaker(*a, **k):
        from reportlab.pdfgen.canvas import Canvas
        k["pageCompression"] = 1
        return Canvas(*a, **k)

    doc.build(elems, onFirstPage=_page_deco, onLaterPages=_page_deco, canvasmaker=_canvasmaker)
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def receipt_pdf(order: Order, payment: Payment) -> bytes:
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    CURRENCY = getattr(settings, "CURRENCY_PREFIX", "RM") or "RM"

    def money(x):
        try:
            return f"{CURRENCY}{float(x or 0):,.2f}"
        except Exception:
            return f"{CURRENCY}0.00"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x, y = 20, 280
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x * mm, y * mm, f"RECEIPT for {getattr(order, 'code', '')}")
    y -= 10
    c.setFont("Helvetica", 10)

    def _fmt_date(d):
        try:
            return getattr(d, "strftime")("%Y-%m-%d")
        except Exception:
            return str(d or "")

    lines = [
        getattr(settings, "COMPANY_NAME", ""),
        getattr(settings, "COMPANY_ADDRESS", ""),
        f"Phone: {getattr(settings, 'COMPANY_PHONE', '')}",
        f"Email: {getattr(settings, 'COMPANY_EMAIL', '')}",
        f"Customer: {getattr(getattr(order, 'customer', None) or type('X',(),{})(), 'name', '-')}",
        f"Payment Date: {_fmt_date(getattr(payment, 'date', None))}",
        f"Amount: {money(getattr(payment, 'amount', 0))}",
        f"Method: {getattr(payment, 'method', '-') or '-'}  Ref: {getattr(payment, 'reference', '-') or '-'}",
        f"Status: {getattr(payment, 'status', '-')}",
        f"Beneficiary: {BENEFICIARY_NAME}",
        f"Bank: {BANK_NAME}",
        f"Account No.: {BANK_ACCOUNT_NO}",
        f"Customer Service: {getattr(settings, 'COMPANY_PHONE', '')}",
    ]
    for t in lines:
        if t:
            c.drawString(x * mm, y * mm, t)
            y -= 6
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# Installment Agreement
# ---------------------------------------------------------------------------

def installment_agreement_pdf(order: Order, plan: Plan) -> bytes:
    try:  # pragma: no cover - exercised indirectly in tests
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:  # pragma: no cover - tested by import
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
    except Exception:
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Title"].fontName = BASE_BOLD
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=14, leading=16))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    elems = []

    def money(x):
        try:
            return f"RM{float(x or 0):,.2f}"
        except Exception:
            return "RM0.00"

    elems.append(
        Paragraph(
            f"INSTALLMENT AGREEMENT ({getattr(order, 'code', '')})",
            styles["Title"],
        )
    )
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(getattr(settings, "COMPANY_NAME", ""), styles["Normal"]))
    elems.append(Paragraph(getattr(settings, "COMPANY_ADDRESS", ""), styles["Small"]))
    elems.append(Spacer(1, 12))

    cust = getattr(order, "customer", None) or type("X", (), {})()
    elems.append(
        Paragraph(
            f"Customer: {getattr(cust, 'name', '')} ({getattr(cust, 'phone', '-')})",
            styles["Normal"],
        )
    )
    addr = getattr(cust, "address", None)
    if addr:
        elems.append(Paragraph(f"Address: {addr}", styles["Normal"]))
    elems.append(
        Paragraph(
            f"Plan: {getattr(plan, 'months', 0)} months at {money(getattr(plan, 'monthly_amount', 0))}/month (no prorate)",
            styles["Normal"],
        )
    )
    elems.append(Spacer(1, 8))
    bullet_terms = [
        "Monthly payments due; no prorate.",
        "If cancel early, penalty equals remaining unpaid instalments plus return delivery fee.",
        "Title remains with company until fully paid.",
    ]
    elems.append(Paragraph("Terms:", styles["H2"]))
    elems.append(Paragraph("<br/>".join(f"• {t}" for t in bullet_terms), styles["Normal"]))
    elems.append(PageBreak())

    elems.append(Paragraph("Terms & Conditions", styles["H2"]))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph("English – “Terms & Conditions”", styles["Normal"]))
    elems.append(Spacer(1, 4))
    english_terms = [
        ("Payment, Default & Remedies. All amounts are due on or before the due date. If you fail to pay any amount when due, we may, to the maximum extent permitted by law: (a) charge late fees and interest; (b) suspend delivery/service and accelerate all amounts outstanding; (c) report the default to credit reporting agencies, including CTOS Data Systems Sdn Bhd; and (d) assign or sell our receivables (including this invoice) to a third-party collector without further consent."),
        ("Data Processing & Privacy Consent. You consent to our collection, use and disclosure of your personal data for account management, payment recovery, fraud prevention and legal compliance, including disclosure to credit reporting agencies (such as CTOS) and appointed collection partners, until all sums are fully settled, subject to applicable law, including the Personal Data Protection Act 2010."),
        ("Ownership & Repossession (Instalment/Rental). Title to goods remains with the Company until full payment is received (for sales) and at all times during rental. Upon default or termination, we may, as permitted by law, enter the location of the goods with reasonable notice (or without notice if legally allowed) to remove and repossess our assets; you must grant access and cooperation. Associated removal, transport and restoration costs are chargeable to you."),
        ("Damage & Loss (Rental). You are responsible for any loss or damage beyond fair wear and tear. Repair, parts and replacement costs (including logistics and technician time) will be charged. If damage renders the equipment unusable, rental charges may continue during downtime caused by your act/omission."),
        ("Delivery, Risk & Insurance. Risk passes on delivery for sales; for rentals, risk of loss/damage remains with you while equipment is in your care. You agree to take reasonable care and, where applicable, maintain suitable insurance."),
        ("Assignment & Third-Party Collection. We may at any time assign, novate or sell any receivables or this agreement to financiers or collection agencies. Your obligations remain unchanged."),
        ("Limitation of Liability. To the maximum extent permitted by law, we are not liable for indirect, special or consequential losses. Our aggregate liability is capped at the price paid for the goods/services giving rise to the claim."),
        ("Governing Law & Jurisdiction. This agreement is governed by the laws of Malaysia. You submit to the exclusive jurisdiction of the courts of Kuala Lumpur."),
        ("Acceptance. By signing, placing the order, taking delivery, or making any payment, you accept these Terms & Conditions."),
    ]
    for para in english_terms:
        elems.append(Paragraph(para, styles["Small"]))
        elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 6))
    elems.append(Paragraph("Bahasa Melayu – “Terma & Syarat”", styles["Normal"]))
    elems.append(Spacer(1, 4))
    malay_terms = [
        ("Pembayaran, Kegagalan & Pemulihan. Semua amaun perlu dibayar pada atau sebelum tarikh akhir. Jika anda gagal membayar, kami boleh, setakat yang dibenarkan undang-undang: (a) mengenakan caj lewat dan faedah; (b) menggantung penghantaran/perkhidmatan dan mempercepatkan semua amaun tertunggak; (c) melaporkan kegagalan bayaran kepada agensi pelaporan kredit termasuk CTOS Data Systems Sdn Bhd; dan (d) menyerah hak atau menjual terimaan kami (termasuk invois ini) kepada pihak pengutip hutang tanpa keizinan lanjut."),
        ("Pemprosesan Data & Persetujuan Privasi. Anda bersetuju bahawa kami boleh mengumpul, menggunakan dan mendedahkan data peribadi anda bagi tujuan pengurusan akaun, pemulihan bayaran, pencegahan penipuan dan pematuhan undang-undang, termasuk pendedahan kepada agensi pelaporan kredit (seperti CTOS) dan rakan kutipan yang dilantik, sehingga semua amaun diselesaikan sepenuhnya, tertakluk kepada undang-undang yang berkenaan termasuk Akta Perlindungan Data Peribadi 2010."),
        ("Pemilikan & Pengambilan Semula (Ansuran/Sewaan). Hak milik kekal milik Syarikat sehingga bayaran penuh diterima (jualan) dan pada setiap masa sepanjang tempoh sewaan. Jika berlaku kegagalan atau penamatan, kami boleh, seperti yang dibenarkan undang-undang, memasuki lokasi barangan dengan notis munasabah (atau tanpa notis jika dibenarkan undang-undang) untuk mengalih keluar dan mengambil balik aset kami; anda hendaklah memberikan akses dan kerjasama. Kos pengalihan, pengangkutan dan pemulihan adalah ditanggung oleh anda."),
        ("Kerosakan & Kehilangan (Sewaan). Anda bertanggungjawab atas sebarang kerosakan atau kehilangan selain daripada haus dan lusuh biasa. Kos pembaikan, alat ganti dan penggantian (termasuk logistik dan masa juruteknik) akan dicajkan. Jika kerosakan menyebabkan peralatan tidak boleh digunakan, caj sewaan boleh diteruskan sepanjang tempoh henti yang berpunca daripada tindakan/kelalaian anda."),
        ("Penghantaran, Risiko & Insurans. Risiko berpindah semasa penghantaran bagi jualan; bagi sewaan, risiko kehilangan/kerosakan berada pada anda sementara peralatan berada dalam jagaan anda. Anda bersetuju menjaga peralatan dengan sewajarnya dan, jika berkenaan, mengekalkan insurans yang sesuai."),
        ("Penyerahan & Pengutipan Pihak Ketiga. Kami boleh pada bila-bila masa menyerah hak, menovat atau menjual mana-mana terimaan atau perjanjian ini kepada pembiaya atau agensi kutipan. Kewajipan anda tidak berubah."),
        ("Had Tanggungan. Setakat yang dibenarkan undang-undang, kami tidak bertanggungan atas kerugian tidak langsung, khas atau berbangkit. Jumlah tanggungan kami terhad kepada harga yang dibayar bagi barangan/perkhidmatan yang berkaitan."),
        ("Undang-undang Mentadbir & Bidang Kuasa. Terma ini ditadbir oleh undang-undang Malaysia. Anda bersetuju tertakluk kepada bidang kuasa eksklusif Mahkamah Kuala Lumpur."),
        ("Penerimaan. Dengan menandatangani, membuat pesanan, menerima penghantaran, atau membuat sebarang pembayaran, anda bersetuju dengan Terma & Syarat ini."),
    ]
    for para in malay_terms:
        elems.append(Paragraph(para, styles["Small"]))
        elems.append(Spacer(1, 4))

    doc.build(elems)
    pdf = buf.getvalue()
    buf.close()
    return pdf
