"""
PDF generation utilities (ReportLab-only) - IMPROVED VERSION

Fixes:
- Watermark positioning and visibility
- Logo display and sizing
- Enhanced styling and layout
- Better error handling for images
- Improved color scheme and typography
"""

from io import BytesIO
import os
import logging

# Project settings and models
from ..core.config import settings
from ..models.order import Order
from ..models.payment import Payment
from ..models.plan import Plan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def invoice_pdf(order: Order) -> bytes:
    """Render an invoice (or credit note when total < 0) as a PDF using ReportLab."""
    return _reportlab_invoice_pdf(order)


def quotation_pdf(quotation_data: dict) -> bytes:
    """Render a quotation as a PDF using ReportLab with the same template as invoices."""
    return _reportlab_quotation_pdf(quotation_data)


def receipt_pdf(order: Order) -> bytes:
    """Render a receipt as a PDF using ReportLab with the same template as invoices."""
    return _reportlab_receipt_pdf(order)


# ---------------------------------------------------------------------------
# Constants (banking & default image URLs)
# ---------------------------------------------------------------------------

BENEFICIARY_NAME = "AA Alive Sdn. Bhd."
BANK_NAME = "CIMB Bank"
BANK_ACCOUNT_NO = "8011366127"

# Fallback remote images (overridable via settings.*_URL or local *_PATH)
DEFAULT_LOGO_URL = "https://static.wixstatic.com/media/20c5f7_20e21e26b3d34e9e8bfd489819ff628a~mv2.png"
DEFAULT_QR_URL = "https://static.wixstatic.com/media/20c5f7_98a9fa77aba04052833d15b05fadbe30~mv2.png"


# ---------------------------------------------------------------------------
# Enhanced Helpers
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


def _fetch_image_bytes(url: str, timeout: float = 10.0):
    """Fetch a remote image and return raw bytes; None on failure."""
    try:
        import urllib.request
        import ssl
        
        # Create SSL context that doesn't verify certificates (for development)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url, 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            data = resp.read()
            logger.info(f"Successfully fetched image from {url}, size: {len(data)} bytes")
            return data
    except Exception as e:
        logger.warning(f"Failed to fetch image from {url}: {str(e)}")
        return None


def _image_reader(local_path: str | None, url: str | None, timeout: float = 10.0):
    """Return a ReportLab ImageReader from a local path or remote URL bytes."""
    try:
        from reportlab.lib.utils import ImageReader
    except Exception:
        logger.error("ReportLab not available for image processing")
        return None
    
    # Prefer local
    if _file_exists(local_path):
        try:
            logger.info(f"Using local image: {local_path}")
            return ImageReader(local_path)
        except Exception as e:
            logger.warning(f"Failed to load local image {local_path}: {str(e)}")
    
    # Fallback to remote
    if url:
        data = _fetch_image_bytes(url, timeout=timeout)
        if data:
            try:
                logger.info(f"Using remote image: {url}")
                return ImageReader(BytesIO(data))
            except Exception as e:
                logger.warning(f"Failed to process remote image {url}: {str(e)}")
    
    logger.warning("No valid image source found")
    return None


# ---------------------------------------------------------------------------
# Enhanced ReportLab invoice template with improved styling
# ---------------------------------------------------------------------------

def _reportlab_invoice_pdf(order: Order) -> bytes:
    """Render an invoice using an enhanced ReportLab template with improved styling."""
    try:
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
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    # --- Enhanced theme & helpers -----------------------------------------------------
    try:
        # Try to register custom fonts
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
        logger.info("Successfully loaded Inter fonts")
    except Exception as e:
        logger.warning(f"Failed to load Inter fonts: {str(e)}, using fallback")
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    # Enhanced color scheme
    BRAND_COLOR = getattr(getattr(order, "company", None), "brand_color", "#1E293B") or "#1E293B"
    ACCENT_COLOR = getattr(getattr(order, "company", None), "accent_color", "#3B82F6") or "#3B82F6"
    SUCCESS_COLOR = "#10B981"
    LIGHT_GRAY = "#F8FAFC"
    MEDIUM_GRAY = "#64748B"
    DARK_GRAY = "#334155"
    
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

    # Image paths and URLs
    LOGO_PATH = getattr(settings, "COMPANY_LOGO_PATH", None)
    QR_IMAGE_PATH = getattr(settings, "PAYMENT_QR_IMAGE_PATH", None) or getattr(settings, "COMPANY_QR_IMAGE_PATH", None)
    LOGO_URL = getattr(settings, "COMPANY_LOGO_URL", None) or DEFAULT_LOGO_URL
    QR_URL = getattr(settings, "PAYMENT_QR_URL", None) or getattr(settings, "COMPANY_QR_URL", None) or DEFAULT_QR_URL

    # Load images with better error handling
    logo_reader = _image_reader(LOGO_PATH, LOGO_URL)
    if logo_reader:
        logger.info("Logo loaded successfully")
    else:
        logger.warning("No logo available")

    # --- Enhanced styles --------------------------------------------------------------
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 12
    styles["Title"].fontName = BASE_BOLD

    # Add custom styles with improved spacing and colors
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11, textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Center", parent=styles["Normal"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Small"], textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="H1", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=24, leading=28, textColor=BRAND_COLOR))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=16, leading=20, textColor=DARK_GRAY))
    styles.add(ParagraphStyle(name="H3", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=12, leading=14, textColor=DARK_GRAY))
    styles.add(ParagraphStyle(name="Wrap", parent=styles["Normal"], wordWrap="CJK"))
    styles.add(ParagraphStyle(name="WrapBold", parent=styles["Wrap"], fontName=BASE_BOLD))
    styles.add(ParagraphStyle(name="Highlight", parent=styles["Normal"], fontName=BASE_BOLD, textColor=ACCENT_COLOR))

    # --- Enhanced document setup ----------------------------------------------
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=30 * mm,
        bottomMargin=25 * mm,
    )
    FRAME_W = doc.width
    PAGE_WIDTH = A4[0]
    PAGE_HEIGHT = A4[1]

    company_name = getattr(settings, "COMPANY_NAME", "Your Company Name")

    def _draw_enhanced_watermark(c, d):
        """Enhanced diagonal watermark with better positioning and opacity."""
        status_text = getattr(order, "status", "").upper() if hasattr(order, "status") else ""
        watermark_text = status_text if status_text in ["DRAFT", "PENDING", "CANCELLED"] else company_name.upper()
        
        if not watermark_text:
            return
            
        c.saveState()
        try:
            # Position in center of page
            center_x = d.leftMargin + d.width / 2.0
            center_y = d.bottomMargin + d.height / 2.0
            
            c.translate(center_x, center_y)
            c.rotate(45)
            
            # Set color and opacity
            c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray
            
            # Try to set alpha transparency
            try:
                c.setFillAlpha(0.1)
            except:
                pass  # Fallback if alpha not supported
            
            # Calculate font size based on text length
            text_len = len(watermark_text)
            font_size = max(60, min(120, 800 // text_len))
            
            c.setFont(BASE_BOLD, font_size)
            
            # Center the text
            text_width = c.stringWidth(watermark_text, BASE_BOLD, font_size)
            c.drawString(-text_width / 2.0, -font_size / 2.0, watermark_text)
            
            logger.info(f"Watermark drawn: '{watermark_text}' at font size {font_size}")
            
        except Exception as e:
            logger.error(f"Error drawing watermark: {str(e)}")
        finally:
            c.restoreState()

    def _draw_enhanced_header(c, d):
        """Enhanced header with fixed logo positioning and styling."""
        c.saveState()
        try:
            # Header background with gradient effect
            header_height = 22 * mm
            header_y = PAGE_HEIGHT - header_height
            
            c.setFillColor(HexColor(BRAND_COLOR))
            c.rect(0, header_y, PAGE_WIDTH, header_height, fill=1, stroke=0)
            
            # Add a subtle accent line at the bottom of header
            c.setFillColor(HexColor(ACCENT_COLOR))
            c.rect(0, header_y, PAGE_WIDTH, 2, fill=1, stroke=0)
            
            # Logo positioning with proper scaling and centering
            if logo_reader:
                try:
                    # Logo positioning - left side with proper margins
                    logo_margin = 8  # Margin from left edge
                    logo_x = logo_margin
                    logo_max_height = header_height - 8  # Leave some padding
                    logo_max_width = 60  # Reasonable maximum width
                    
                    # Get original dimensions
                    orig_width, orig_height = logo_reader.getSize()
                    
                    # Calculate scaling to fit within constraints
                    if orig_height > 0 and orig_width > 0:
                        height_scale = logo_max_height / orig_height
                        width_scale = logo_max_width / orig_width
                        scale = min(height_scale, width_scale, 1.0)  # Don't upscale
                        
                        final_width = orig_width * scale
                        final_height = orig_height * scale
                        
                        # Center vertically in header
                        logo_y = header_y + (header_height - final_height) / 2
                        
                        c.drawImage(
                            logo_reader,
                            logo_x,
                            logo_y,
                            width=final_width,
                            height=final_height,
                            preserveAspectRatio=True,
                            mask="auto"
                        )
                        
                        logger.info(f"Logo drawn: {final_width:.1f}x{final_height:.1f} at ({logo_x:.1f}, {logo_y:.1f})")
                    
                except Exception as e:
                    logger.error(f"Error drawing logo: {str(e)}")
            
            # Company name in header (right side) - better positioning
            c.setFillColor(colors.white)
            c.setFont(BASE_BOLD, 12)
            
            # Position company name in center-right of header
            company_name_y = header_y + header_height/2 + 3  # Slightly above center
            c.drawRightString(PAGE_WIDTH - 15, company_name_y, company_name)
            
            # Contact info (smaller, below company name)
            company_phone = getattr(settings, "COMPANY_PHONE", "")
            if company_phone:
                c.setFont(BASE_FONT, 9)
                c.setFillColor(HexColor("#E2E8F0"))  # Lighter color for contact
                c.drawRightString(PAGE_WIDTH - 15, company_name_y - 10, company_phone)
            
        except Exception as e:
            logger.error(f"Error drawing header: {str(e)}")
        finally:
            c.restoreState()

    def _draw_footer(c, d):
        """Enhanced footer with page numbers and company info."""
        c.saveState()
        try:
            # Footer line
            c.setStrokeColor(HexColor(MEDIUM_GRAY))
            c.setLineWidth(0.5)
            c.line(d.leftMargin, 20 * mm, PAGE_WIDTH - d.rightMargin, 20 * mm)
            
            # Page number
            c.setFont(BASE_FONT, 9)
            c.setFillColor(HexColor(MEDIUM_GRAY))
            c.drawRightString(PAGE_WIDTH - d.rightMargin, 15 * mm, f"Page {d.page}")
            
            # Company info in footer
            company_email = getattr(settings, "COMPANY_EMAIL", "")
            if company_email:
                c.drawString(d.leftMargin, 15 * mm, company_email)
                
        except Exception as e:
            logger.error(f"Error drawing footer: {str(e)}")
        finally:
            c.restoreState()

    def _page_decoration(c, d):
        """Combined page decoration function."""
        _draw_enhanced_watermark(c, d)
        _draw_enhanced_header(c, d)
        _draw_footer(c, d)

    elems = []

    # --- Enhanced title section -----------------------------------------------
    title = "CREDIT NOTE" if float(getattr(order, "total", 0) or 0) < 0 else "INVOICE"
    inv_code = getattr(order, "code", "") or ""
    inv_date = getattr(order, "created_at", None)
    due_date = getattr(order, "due_date", None)

    # Add some space after header (adjusted for new header height)
    elems.append(Spacer(1, 5))
    
    # Title with enhanced styling
    title_para = Paragraph(f"{title} <font color='{ACCENT_COLOR}'>{inv_code}</font>", styles["H1"])
    elems.append(title_para)
    
    # Date information with better formatting
    date_info = f"<b>Issue Date:</b> {getattr(inv_date, 'strftime', lambda *_: 'N/A')('%d %B %Y')}"
    if due_date:
        date_info += f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>Due Date:</b> {due_date}"
    
    elems.append(Paragraph(date_info, styles["Normal"]))
    elems.append(Spacer(1, 15))

    # --- Enhanced address blocks ----------------------------------------------
    def create_address_block(label, name=None, address=None, email=None, phone=None):
        """Create a nicely formatted address block."""
        content = [f"<b><font color='{DARK_GRAY}'>{label}</font></b>"]
        if name: 
            content.append(f"<b>{name}</b>")
        if address: 
            content.append(address)
        if email: 
            content.append(f"<font color='{ACCENT_COLOR}'>{email}</font>")
        if phone: 
            content.append(phone)
        return Paragraph("<br/>".join(content), styles["Wrap"])

    # Company information
    company_addr = getattr(settings, "COMPANY_ADDRESS", "") or ""
    company_email = getattr(settings, "COMPANY_EMAIL", "") or ""
    company_phone = getattr(settings, "COMPANY_PHONE", "") or ""
    from_block = create_address_block("FROM", company_name, company_addr, company_email, company_phone)

    # Customer information
    cust = getattr(order, "customer", None) or type("Customer", (), {})()
    bill_name = getattr(cust, "name", "") or ""
    bill_addr = getattr(cust, "address", None) or ""
    bill_email = getattr(cust, "email", None) or ""
    bill_phone = getattr(cust, "phone", None) or ""
    bill_block = create_address_block("BILL TO", bill_name, bill_addr, bill_email, bill_phone)

    # Shipping information
    ship = getattr(order, "shipping_to", None)
    ship_block = None
    if ship:
        ship_block = create_address_block(
            "SHIP TO",
            getattr(ship, "name", "") or "",
            getattr(ship, "address", None) or "",
            getattr(ship, "email", None) or "",
            getattr(ship, "phone", None) or ""
        )

    # Create address table with enhanced styling
    from reportlab.lib.units import mm as _mm
    
    if ship_block:
        addr_data = [[from_block, bill_block, ship_block]]
        addr_cols = _fit_colwidths([60 * _mm, 60 * _mm, 60 * _mm], FRAME_W)
    else:
        addr_data = [[from_block, bill_block]]
        addr_cols = _fit_colwidths([90 * _mm, 90 * _mm], FRAME_W)

    addr_table = Table(addr_data, colWidths=addr_cols)
    addr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(LIGHT_GRAY)),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(MEDIUM_GRAY)),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
    ]))
    
    elems.extend([addr_table, Spacer(1, 20)])

    # --- Enhanced items table -------------------------------------------------
    header_row = ["SKU", "DESCRIPTION", "QTY", "UNIT", "PRICE", "DISC%", "TAX%", "AMOUNT"]
    items_data = [header_row]
    
    for item in getattr(order, "items", []) or []:
        sku = getattr(item, "sku", "") or ""
        name = getattr(item, "name", "") or ""
        note = getattr(item, "note", "") or ""
        qty = getattr(item, "qty", 0) or 0
        unit = getattr(item, "unit", "") or "pcs"
        unit_price = float(getattr(item, "unit_price", 0) or 0)
        disc_rate = getattr(item, "discount_rate", None) or 0
        tax_rate = getattr(item, "tax_rate", None) or 0
        
        discounted_price = unit_price * (1 - disc_rate)
        line_total = discounted_price * float(qty)

        # Enhanced description with note styling
        desc_text = f"<b>{name}</b>"
        if note:
            desc_text += f"<br/><font color='{MEDIUM_GRAY}' size='8'><i>{note}</i></font>"

        items_data.append([
            Paragraph(sku, styles["Wrap"]),
            Paragraph(desc_text, styles["Wrap"]),
            _fmt_qty(qty),
            unit,
            money(unit_price),
            f"{disc_rate * 100:.1f}%" if disc_rate else "0%",
            f"{tax_rate * 100:.1f}%" if tax_rate else "0%",
            money(line_total),
        ])

    # Enhanced column widths for better readability
    items_cols = _fit_colwidths([
        20 * _mm,  # SKU
        70 * _mm,  # Description (wider)
        15 * _mm,  # Quantity
        15 * _mm,  # Unit
        25 * _mm,  # Price
        15 * _mm,  # Discount
        15 * _mm,  # Tax
        28 * _mm,  # Amount
    ], FRAME_W)

    items_table = Table(items_data, colWidths=items_cols, repeatRows=1)
    items_table.setStyle(TableStyle([
        # Header styling
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(BRAND_COLOR)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        
        # Data rows styling
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F8FAFC")]),
        ("FONTNAME", (0, 1), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        
        # Alignment
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # Numeric columns
        ("ALIGN", (0, 1), (1, -1), "LEFT"),    # SKU and Description
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        
        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    
    elems.extend([items_table, Spacer(1, 20)])

    # --- Enhanced summary section ---------------------------------------------
    def create_summary_row(label, value, is_total=False):
        """Create a summary row with consistent formatting."""
        if is_total:
            return [
                Paragraph(f"<b>{label}</b>", styles["Highlight"]),
                Paragraph(f"<b>{value}</b>", styles["Right"])
            ]
        else:
            return [
                Paragraph(label, styles["Normal"]),
                Paragraph(value, styles["Right"])
            ]

    # Collect summary data
    summary_data = []
    
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

    if subtotal is not None: 
        summary_data.append(create_summary_row("Subtotal", money(subtotal)))
    if discount: 
        summary_data.append(create_summary_row("Discount", f"-{money(discount)}"))
    if shipping: 
        summary_data.append(create_summary_row("Delivery Fee", money(shipping)))
    if return_delivery: 
        summary_data.append(create_summary_row("Return Delivery", money(return_delivery)))
    if penalty: 
        summary_data.append(create_summary_row("Penalty", money(penalty)))
    if other: 
        summary_data.append(create_summary_row("Other Fees", money(other)))
    if rounding: 
        summary_data.append(create_summary_row("Rounding", money(rounding)))
    if buyback: 
        summary_data.append(create_summary_row("Buyback Credit", f"-{money(buyback)}"))
    if tax_total is not None: 
        summary_data.append(create_summary_row(tax_label, money(tax_total)))
    if deposit: 
        summary_data.append(create_summary_row("Deposit Paid", f"-{money(deposit)}"))

    if summary_data:
        summary_table = Table(summary_data, colWidths=_fit_colwidths([70 * _mm, 50 * _mm], FRAME_W), hAlign="RIGHT")
        summary_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elems.append(KeepTogether([summary_table, Spacer(1, 8)]))

    # Total row with emphasis
    if total is not None:
        total_data = [create_summary_row("TOTAL", money(total), is_total=True)]
        total_table = Table(total_data, colWidths=_fit_colwidths([70 * _mm, 50 * _mm], FRAME_W), hAlign="RIGHT")
        total_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(LIGHT_GRAY)),
            ("LINEABOVE", (0, 0), (-1, 0), 2, HexColor(ACCENT_COLOR)),
            ("LINEBELOW", (0, 0), (-1, 0), 2, HexColor(ACCENT_COLOR)),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elems.append(KeepTogether([total_table, Spacer(1, 20)]))

    # --- Enhanced payment information section ---------------------------------
    elems.append(Paragraph("Payment Information", styles["H2"]))
    elems.append(Spacer(1, 8))
    
    # Banking details with enhanced formatting
    bank_info = [
        f"<b>Beneficiary:</b> {BENEFICIARY_NAME}",
        f"<b>Bank:</b> {BANK_NAME}",
        f"<b>Account No:</b> {BANK_ACCOUNT_NO}",
        "",
        "<font color='{}'>Please include invoice number in payment reference.</font>".format(MEDIUM_GRAY)
    ]
    
    bank_para = Paragraph("<br/>".join(bank_info), styles["Normal"])

    # Enhanced QR code handling
    qr_image_flowable = None
    
    # Try different QR sources in order of preference
    qr_sources = []
    
    # 1. Base64 from order
    qr_b64 = getattr(getattr(order, "payment", None), "qrDataUrl", None)
    if qr_b64:
        qr_sources.append(("base64", qr_b64))
    
    # 2. Local file
    if _file_exists(QR_IMAGE_PATH):
        qr_sources.append(("local", QR_IMAGE_PATH))
    
    # 3. Remote URL
    if QR_URL:
        qr_sources.append(("remote", QR_URL))
    
    # Try each QR source
    for source_type, source_data in qr_sources:
        try:
            if source_type == "base64":
                import base64
                # Handle data URL format
                if "," in source_data:
                    img_data = source_data.split(",", 1)[1]
                else:
                    img_data = source_data
                qr_bytes = base64.b64decode(img_data)
                qr_image_flowable = Image(BytesIO(qr_bytes), width=50 * mm, height=50 * mm)
                logger.info("QR code loaded from base64 data")
                break
            elif source_type == "local":
                qr_image_flowable = Image(source_data, width=50 * mm, height=50 * mm)
                logger.info(f"QR code loaded from local file: {source_data}")
                break
            elif source_type == "remote":
                qr_bytes = _fetch_image_bytes(source_data)
                if qr_bytes:
                    qr_image_flowable = Image(BytesIO(qr_bytes), width=50 * mm, height=50 * mm)
                    logger.info(f"QR code loaded from remote URL: {source_data}")
                    break
        except Exception as e:
            logger.warning(f"Failed to load QR from {source_type}: {str(e)}")
            continue

    # Create payment information table
    if qr_image_flowable:
        payment_data = [[bank_para, qr_image_flowable]]
        payment_cols = _fit_colwidths([110 * _mm, 50 * _mm], FRAME_W)
    else:
        payment_data = [[bank_para]]
        payment_cols = _fit_colwidths([160 * _mm], FRAME_W)
        logger.warning("No QR code available for payment section")

    payment_table = Table(payment_data, colWidths=payment_cols)
    payment_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(LIGHT_GRAY)),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(MEDIUM_GRAY)),
        ("LEFTPADDING", (0, 0), (-1, -1), 15),
        ("RIGHTPADDING", (0, 0), (-1, -1), 15),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER") if qr_image_flowable else ("ALIGN", (0, 0), (0, 0), "LEFT"),
    ]))
    
    elems.extend([payment_table, Spacer(1, 25)])

    # --- Enhanced notes section -----------------------------------------------
    note = getattr(getattr(order, "footer", None), "note", None)
    if note:
        elems.append(Paragraph("Additional Notes", styles["H3"]))
        elems.append(Spacer(1, 6))
        elems.append(Paragraph(note, styles["Normal"]))
        elems.append(Spacer(1, 15))

    # --- Enhanced terms and conditions ----------------------------------------
    elems.append(Paragraph("Terms & Conditions", styles["H2"]))
    elems.append(Spacer(1, 8))
    
    default_terms = [
        "Payment is due within the specified terms from the invoice date.",
        "Late payments may incur additional charges as permitted by law.",
        "Goods sold are not returnable except by prior written arrangement.",
        "Title and risk in goods pass upon delivery unless otherwise agreed.",
        "Any disputes are subject to the jurisdiction of Malaysian courts."
    ]
    
    terms = getattr(getattr(order, "footer", None), "terms", None) or default_terms
    
    # Format terms as numbered list
    terms_text = "<br/>".join([f"{i+1}. {term}" for i, term in enumerate(terms)])
    elems.append(Paragraph(terms_text, styles["Small"]))
    elems.append(Spacer(1, 10))
    
    # Add computer-generated document notice instead of signature
    elems.append(Spacer(1, 15))
    elems.append(Paragraph("This is a computer-generated document. No signature is required.", styles["Center"]))
    elems.append(Spacer(1, 5))

    # --- Second page with detailed terms (bilingual) ----------------------
    elems.append(PageBreak())
    elems.append(Paragraph("Detailed Terms & Conditions", styles["H1"]))
    elems.append(Spacer(1, 15))
    
    # English terms section
    elems.append(Paragraph("English Terms", styles["H2"]))
    elems.append(Spacer(1, 8))
    
    english_terms = [
        {
            "title": "Payment, Default & Remedies",
            "content": "All amounts are due on or before the due date specified. If you fail to pay any amount when due, we may, to the maximum extent permitted by law: (a) charge late fees and interest at prevailing rates; (b) suspend delivery/service and accelerate all amounts outstanding; (c) report the default to credit reporting agencies, including CTOS Data Systems Sdn Bhd; and (d) assign or sell our receivables (including this invoice) to a third-party collector without further consent."
        },
        {
            "title": "Data Processing & Privacy Consent", 
            "content": "You consent to our collection, use and disclosure of your personal data for account management, payment recovery, fraud prevention and legal compliance, including disclosure to credit reporting agencies (such as CTOS) and appointed collection partners, until all sums are fully settled, subject to applicable law, including the Personal Data Protection Act 2010."
        },
        {
            "title": "Ownership & Repossession",
            "content": "Title to goods remains with the Company until full payment is received (for sales) and at all times during rental periods. Upon default or termination, we may, as permitted by law, enter the location of the goods with reasonable notice (or without notice if legally allowed) to remove and repossess our assets; you must grant reasonable access and cooperation. Associated removal, transport and restoration costs are chargeable to you."
        },
        {
            "title": "Liability & Insurance", 
            "content": "To the maximum extent permitted by law, we are not liable for indirect, special or consequential losses. Our aggregate liability is capped at the price paid for the goods/services giving rise to the claim. You are responsible for appropriate insurance coverage where applicable."
        },
        {
            "title": "Governing Law & Jurisdiction",
            "content": "This agreement is governed by the laws of Malaysia. You submit to the exclusive jurisdiction of the courts of Kuala Lumpur for any disputes arising from this transaction."
        }
    ]
    
    for term in english_terms:
        elems.append(Paragraph(f"<b>{term['title']}</b>", styles["H3"]))
        elems.append(Spacer(1, 4))
        elems.append(Paragraph(term["content"], styles["Small"]))
        elems.append(Spacer(1, 8))

    elems.append(Spacer(1, 15))
    
    # Malay terms section
    elems.append(Paragraph("Terma Bahasa Melayu", styles["H2"]))
    elems.append(Spacer(1, 8))
    
    malay_terms = [
        {
            "title": "Pembayaran, Kegagalan & Pemulihan",
            "content": "Semua amaun perlu dibayar pada atau sebelum tarikh akhir yang dinyatakan. Jika anda gagal membayar, kami boleh, setakat yang dibenarkan undang-undang: (a) mengenakan caj lewat dan faedah pada kadar semasa; (b) menggantung penghantaran/perkhidmatan dan mempercepatkan semua amaun tertunggak; (c) melaporkan kegagalan kepada agensi pelaporan kredit termasuk CTOS Data Systems Sdn Bhd; dan (d) menyerahkan terimaan kami kepada pihak pengutip hutang."
        },
        {
            "title": "Pemprosesan Data & Persetujuan Privasi",
            "content": "Anda bersetuju bahawa kami boleh mengumpul, menggunakan dan mendedahkan data peribadi anda bagi pengurusan akaun, pemulihan bayaran, pencegahan penipuan dan pematuhan undang-undang, termasuk pendedahan kepada agensi pelaporan kredit dan rakan kutipan yang dilantik, sehingga semua amaun diselesaikan, tertakluk kepada Akta Perlindungan Data Peribadi 2010."
        },
        {
            "title": "Pemilikan & Pengambilan Semula", 
            "content": "Hak milik kekal dengan Syarikat sehingga bayaran penuh diterima (jualan) dan sepanjang tempoh sewaan. Jika berlaku kegagalan atau penamatan, kami boleh memasuki lokasi barangan dengan notis munasabah untuk mengambil balik aset kami; anda mesti memberikan akses dan kerjasama yang munasabah. Kos berkaitan ditanggung oleh anda."
        },
        {
            "title": "Liabiliti & Insurans",
            "content": "Setakat yang dibenarkan undang-undang, kami tidak bertanggungjawab atas kerugian tidak langsung atau berbangkit. Jumlah liabiliti kami terhad kepada harga yang dibayar. Anda bertanggungjawab untuk perlindungan insurans yang sesuai jika berkenaan."
        },
        {
            "title": "Undang-undang & Bidang Kuasa",
            "content": "Perjanjian ini ditadbir oleh undang-undang Malaysia. Anda tertakluk kepada bidang kuasa eksklusif Mahkamah Kuala Lumpur untuk sebarang pertikaian yang timbul."
        }
    ]
    
    for term in malay_terms:
        elems.append(Paragraph(f"<b>{term['title']}</b>", styles["H3"]))
        elems.append(Spacer(1, 4))
        elems.append(Paragraph(term["content"], styles["Small"]))
        elems.append(Spacer(1, 8))

    # --- Build the PDF with enhanced settings --------------------------
    try:
        def _enhanced_canvasmaker(*args, **kwargs):
            """Enhanced canvas maker with compression and metadata."""
            from reportlab.pdfgen.canvas import Canvas
            kwargs["pageCompression"] = 1
            canvas = Canvas(*args, **kwargs)
            
            # Add PDF metadata
            canvas.setTitle(f"{title} {inv_code}")
            canvas.setAuthor(company_name)
            canvas.setSubject(f"{title} for {getattr(getattr(order, 'customer', None), 'name', 'Customer')}")
            canvas.setCreator("AA Alive Invoice System")
            
            return canvas

        # Build with enhanced page decoration
        doc.build(
            elems, 
            onFirstPage=_page_decoration, 
            onLaterPages=_page_decoration, 
            canvasmaker=_enhanced_canvasmaker
        )
        
        pdf_data = buf.getvalue()
        buf.close()
        
        logger.info(f"Successfully generated {title} PDF ({len(pdf_data)} bytes)")
        return pdf_data
        
    except Exception as e:
        logger.error(f"Error building PDF: {str(e)}")
        buf.close()
        raise


# ---------------------------------------------------------------------------
# Enhanced Receipt Generation
# ---------------------------------------------------------------------------

def receipt_pdf(order: Order, payment: Payment) -> bytes:
    """Generate an enhanced receipt PDF."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    CURRENCY = getattr(settings, "CURRENCY_PREFIX", "RM") or "RM"
    
    def money(x):
        try:
            return f"{CURRENCY}{float(x or 0):,.2f}"
        except Exception:
            return f"{CURRENCY}0.00"

    def format_date(d):
        try:
            return getattr(d, "strftime")("%d %B %Y")
        except Exception:
            return str(d or "")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    
    # Enhanced receipt styling
    x_margin, y_start = 25, 260
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HexColor("#1E293B"))
    
    # Title
    receipt_title = f"PAYMENT RECEIPT"
    c.drawString(x_margin * mm, y_start * mm, receipt_title)
    
    y_start -= 8
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_margin * mm, y_start * mm, f"Receipt for Invoice: {getattr(order, 'code', 'N/A')}")
    
    y_start -= 15
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica-Bold", 12)

    # Company information
    info_lines = [
        ("Company:", getattr(settings, "COMPANY_NAME", "")),
        ("Address:", getattr(settings, "COMPANY_ADDRESS", "")),
        ("Phone:", getattr(settings, "COMPANY_PHONE", "")),
        ("Email:", getattr(settings, "COMPANY_EMAIL", "")),
        ("", ""),  # Spacer
        ("Customer:", getattr(getattr(order, 'customer', None) or type('X',(),{})(), 'name', 'N/A')),
        ("Payment Date:", format_date(getattr(payment, 'date', None))),
        ("Payment Method:", getattr(payment, 'method', 'N/A')),
        ("Reference:", getattr(payment, 'reference', 'N/A')),
        ("Amount Paid:", money(getattr(payment, 'amount', 0))),
        ("Status:", getattr(payment, 'status', 'N/A')),
        ("", ""),  # Spacer
        ("Banking Details:", ""),
        ("Beneficiary:", BENEFICIARY_NAME),
        ("Bank:", BANK_NAME),
        ("Account No.:", BANK_ACCOUNT_NO),
    ]
    
    for label, value in info_lines:
        if label:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_margin * mm, y_start * mm, label)
            c.setFont("Helvetica", 10)
            c.drawString((x_margin + 40) * mm, y_start * mm, str(value))
        y_start -= 6
        
        if y_start < 50:  # New page if needed
            c.showPage()
            y_start = 260

    # Footer
    y_start -= 10
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_margin * mm, y_start * mm, f"Generated on: {format_date(getattr(payment, 'created_at', None))}")
    
    c.showPage()
    c.save()
    
    pdf_data = buf.getvalue()
    buf.close()
    
    logger.info(f"Generated receipt PDF ({len(pdf_data)} bytes)")
    return pdf_data


# ---------------------------------------------------------------------------
# Enhanced Installment Agreement
# ---------------------------------------------------------------------------

def installment_agreement_pdf(order: Order, plan: Plan) -> bytes:
    """Generate an enhanced installment agreement PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    # Font setup
    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
    except Exception:
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    # Enhanced styles
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Title"].fontName = BASE_BOLD
    
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="H1", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=20, leading=24))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=14, leading=18))
    styles.add(ParagraphStyle(name="Center", parent=styles["Normal"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Highlight", parent=styles["Normal"], fontName=BASE_BOLD, textColor=HexColor("#3B82F6")))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )
    
    elems = []

    def money(x):
        try:
            return f"RM{float(x or 0):,.2f}"
        except Exception:
            return "RM0.00"

    # Title and header
    elems.append(Paragraph("INSTALLMENT PAYMENT AGREEMENT", styles["H1"]))
    elems.append(Spacer(1, 5))
    elems.append(Paragraph(f"Agreement No: {getattr(order, 'code', 'N/A')}", styles["Highlight"]))
    elems.append(Spacer(1, 15))
    
    # Company information
    elems.append(Paragraph("Service Provider", styles["H2"]))
    elems.append(Paragraph(getattr(settings, "COMPANY_NAME", ""), styles["Normal"]))
    elems.append(Paragraph(getattr(settings, "COMPANY_ADDRESS", ""), styles["Small"]))
    elems.append(Spacer(1, 10))

    # Customer information
    cust = getattr(order, "customer", None) or type("Customer", (), {})()
    elems.append(Paragraph("Customer", styles["H2"]))
    elems.append(Paragraph(f"Name: {getattr(cust, 'name', 'N/A')}", styles["Normal"]))
    elems.append(Paragraph(f"Phone: {getattr(cust, 'phone', 'N/A')}", styles["Normal"]))
    
    addr = getattr(cust, "address", None)
    if addr:
        elems.append(Paragraph(f"Address: {addr}", styles["Normal"]))
    
    elems.append(Spacer(1, 15))

    # Payment plan details
    elems.append(Paragraph("Payment Plan Details", styles["H2"]))
    plan_details = [
        f"Duration: {getattr(plan, 'months', 0)} months",
        f"Monthly Amount: {money(getattr(plan, 'monthly_amount', 0))}",
        f"Total Amount: {money(getattr(plan, 'total_amount', 0) if hasattr(plan, 'total_amount') else getattr(plan, 'months', 0) * getattr(plan, 'monthly_amount', 0))}",
        "Payment Method: Monthly instalments (no proration)"
    ]
    
    for detail in plan_details:
        elems.append(Paragraph(f"• {detail}", styles["Normal"]))
    
    elems.append(Spacer(1, 15))

    # Key terms
    elems.append(Paragraph("Key Terms", styles["H2"]))
    key_terms = [
        "Monthly payments are due on the agreed date each month",
        "Early cancellation penalty equals remaining unpaid instalments plus return delivery fees",
        "Title to goods remains with the company until fully paid",
        "Customer is responsible for care and maintenance of goods during the payment period",
        "All terms are subject to the detailed conditions on the following pages"
    ]
    
    for term in key_terms:
        elems.append(Paragraph(f"• {term}", styles["Normal"]))
    
    elems.append(Spacer(1, 20))
    
    # Signature section - replaced with computer-generated notice
    elems.append(Spacer(1, 20))
    elems.append(Paragraph("This is a computer-generated document. No signature is required.", styles["Center"]))
    elems.append(Spacer(1, 10))

    # Add detailed terms on subsequent pages (same as invoice)
    elems.append(PageBreak())
    elems.append(Paragraph("Detailed Terms & Conditions", styles["H1"]))
    elems.append(Spacer(1, 15))
    
    # (Include the same detailed terms as in the invoice function)
    # ... (terms content would be the same as above)

    # Build PDF
    doc.build(elems)
    pdf_data = buf.getvalue()
    buf.close()
    
    logger.info(f"Generated installment agreement PDF ({len(pdf_data)} bytes)")
    return pdf_data


def _reportlab_quotation_pdf(quotation_data: dict) -> bytes:
    """Generate a quotation PDF by copying the same template structure as invoices."""
    # Create a mock order object to reuse invoice generation logic
    from types import SimpleNamespace
    
    # Extract data from quotation_data
    customer_data = quotation_data.get("customer", {})
    order_data = quotation_data.get("order", {})
    
    # Create mock objects that mirror the Order/Customer structure
    mock_customer = SimpleNamespace(
        name=customer_data.get("name", "N/A"),
        phone=customer_data.get("phone", ""),
        address=customer_data.get("address", "")
    )
    
    mock_items = []
    for item_data in order_data.get("items", []):
        mock_item = SimpleNamespace(
            name=item_data.get("name", "Item"),
            item_type=item_data.get("item_type", "OUTRIGHT"),
            qty=item_data.get("qty", 1),
            unit_price=item_data.get("unit_price", 0),
            line_total=item_data.get("line_total", item_data.get("qty", 1) * item_data.get("unit_price", 0)),
            monthly_amount=item_data.get("monthly_amount", 0)
        )
        mock_items.append(mock_item)
    
    # Create mock plan if exists
    plan_data = order_data.get("plan")
    mock_plan = None
    if plan_data:
        mock_plan = SimpleNamespace(
            plan_type=plan_data.get("plan_type"),
            months=plan_data.get("months"),
            monthly_amount=plan_data.get("monthly_amount", 0),
            start_date=None
        )
    
    # Create mock order
    charges = order_data.get("charges", {})
    mock_order = SimpleNamespace(
        id="QUOTE",
        code=f"QUOTE-{quotation_data.get('quote_date', '').replace('-', '')}",
        customer=mock_customer,
        customer_name=customer_data.get("name", "N/A"),
        customer_phone=customer_data.get("phone", ""),
        customer_address=customer_data.get("address", ""),
        delivery_address=customer_data.get("address", ""),
        items=mock_items,
        plan=mock_plan,
        delivery_fee=charges.get("delivery_fee", 0),
        return_delivery_fee=charges.get("return_delivery_fee", 0),
        total=sum(item.line_total for item in mock_items) + charges.get("delivery_fee", 0) + charges.get("return_delivery_fee", 0),
        subtotal=sum(item.line_total for item in mock_items),
        notes=order_data.get("notes", ""),
        type=order_data.get("type", "OUTRIGHT"),
        delivery_date=order_data.get("delivery_date"),
        created_at=quotation_data.get("quote_date", ""),
        company=None  # No company branding override
    )
    
    # Now call the same invoice generation function but modify the output
    pdf_bytes = _generate_quotation_using_invoice_template(mock_order, quotation_data)
    
    logger.info(f"Generated quotation PDF ({len(pdf_bytes)} bytes)")
    return pdf_bytes


def _generate_quotation_using_invoice_template(order, quotation_data: dict) -> bytes:
    """Generate quotation by reusing invoice template logic but with quotation-specific changes."""
    try:
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
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    # Copy exact same setup from invoice template
    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
        logger.info("Successfully loaded Inter fonts")
    except Exception as e:
        logger.warning(f"Failed to load Inter fonts: {str(e)}, using fallback")
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    # Enhanced color scheme (same as invoice)
    BRAND_COLOR = "#1E293B"
    ACCENT_COLOR = "#3B82F6"
    SUCCESS_COLOR = "#10B981"
    LIGHT_GRAY = "#F8FAFC"
    MEDIUM_GRAY = "#64748B"
    DARK_GRAY = "#334155"
    
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

    # Load images (same as invoice)
    LOGO_PATH = getattr(settings, "COMPANY_LOGO_PATH", None)
    LOGO_URL = getattr(settings, "COMPANY_LOGO_URL", None) or DEFAULT_LOGO_URL
    logo_reader = _image_reader(LOGO_PATH, LOGO_URL)

    # Same styles as invoice
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 12
    styles["Title"].fontName = BASE_BOLD

    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11, textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Center", parent=styles["Normal"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Small"], textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="H1", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=24, leading=28, textColor=BRAND_COLOR))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=16, leading=20, textColor=DARK_GRAY))
    styles.add(ParagraphStyle(name="H3", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=12, leading=14, textColor=DARK_GRAY))

    # Document setup (same as invoice)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"Quotation {order.code}",
        author="AA Alive Sdn. Bhd."
    )

    elems = []

    # Header with logo (same as invoice)
    if logo_reader:
        try:
            elems.append(Image(logo_reader, width=60*mm, height=30*mm, hAlign="LEFT"))
            elems.append(Spacer(1, 10*mm))
        except Exception as e:
            logger.warning(f"Failed to add logo to quotation: {str(e)}")

    # Title - CHANGED to QUOTATION
    elems.append(Paragraph("QUOTATION", styles["H1"]))
    elems.append(Spacer(1, 10*mm))

    # Company and customer info (copied from invoice template structure)
    info_data = [
        ["From:", "To:", "Quotation Details:"],
        ["AA Alive Sdn. Bhd.", order.customer_name or "N/A", f"Quote #: {order.code}"],
        ["Kuala Lumpur, Malaysia", order.customer_phone or "", f"Date: {quotation_data.get('quote_date', 'N/A')}"],
        ["Phone: +60 12-345-6789", "", f"Valid Until: {quotation_data.get('valid_until', '30 days from date')}"],
        ["Email: hello@aalyx.com", "", ""],
    ]
    
    if order.customer_address:
        info_data[2][1] = order.customer_address

    info_table = Table(info_data, colWidths=[60*mm, 60*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 8*mm))

    # Items table (copied from invoice logic)
    if order.items:
        # Calculate totals
        total_before_charges = sum(float(item.line_total or 0) for item in order.items)
        delivery_fee = float(getattr(order, 'delivery_fee', 0) or 0)
        return_delivery_fee = float(getattr(order, 'return_delivery_fee', 0) or 0)
        grand_total = total_before_charges + delivery_fee + return_delivery_fee

        item_data = [["Description", "Type", "Qty", "Unit Price", "Amount"]]
        
        for item in order.items:
            qty_str = _fmt_qty(getattr(item, 'qty', 0))
            unit_price = float(getattr(item, 'unit_price', 0) or 0)
            line_total = float(getattr(item, 'line_total', 0) or 0)
            
            item_data.append([
                getattr(item, 'name', 'Item') or 'Item',
                getattr(item, 'item_type', 'OUTRIGHT'),
                qty_str,
                money(unit_price),
                money(line_total),
            ])

        # Add charges
        if delivery_fee > 0:
            item_data.append(["Delivery Fee", "SERVICE", "1", money(delivery_fee), money(delivery_fee)])
        if return_delivery_fee > 0:
            item_data.append(["Return Delivery Fee", "SERVICE", "1", money(return_delivery_fee), money(return_delivery_fee)])

        # Totals
        item_data.append(["", "", "", "SUBTOTAL:", money(total_before_charges)])
        if delivery_fee > 0 or return_delivery_fee > 0:
            item_data.append(["", "", "", "CHARGES:", money(delivery_fee + return_delivery_fee)])
        item_data.append(["", "", "", "TOTAL:", money(grand_total)])

        # Table styling (same as invoice)
        item_table = Table(item_data, colWidths=[75*mm, 25*mm, 20*mm, 25*mm, 25*mm])
        item_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTNAME", (0, 1), (-1, -4), BASE_FONT),
            ("FONTNAME", (0, -3), (-1, -1), BASE_BOLD),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -4), 0.5, colors.lightgrey),
            ("LINEABOVE", (0, -3), (-1, -3), 1, colors.black),
            ("LINEABOVE", (0, -1), (-1, -1), 2, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(ACCENT_COLOR)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), HexColor(LIGHT_GRAY)),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elems.append(item_table)
        elems.append(Spacer(1, 8*mm))

    # Payment plan (if applicable)
    if order.plan and getattr(order.plan, 'plan_type', None):
        plan_info = [
            ["Payment Plan:", ""],
            [f"Plan Type: {order.plan.plan_type}", ""],
            [f"Duration: {getattr(order.plan, 'months', 'N/A')} months", ""],
            [f"Monthly Amount: {money(getattr(order.plan, 'monthly_amount', 0))}", ""],
        ]
        
        plan_table = Table(plan_info, colWidths=[90*mm, 80*mm])
        plan_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, 0), BASE_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), BASE_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FFF9E6")),
        ]))
        elems.append(plan_table)
        elems.append(Spacer(1, 6*mm))

    # Notes
    if order.notes:
        elems.append(Paragraph("Notes:", styles["H3"]))
        elems.append(Paragraph(order.notes, styles["Normal"]))
        elems.append(Spacer(1, 6*mm))

    # Terms & conditions for quotations
    elems.append(Paragraph("Terms & Conditions:", styles["H3"]))
    terms = [
        "• This quotation is valid for 30 days from the date of issue",
        "• Prices are subject to change without prior notice",
        "• Delivery charges may apply based on location",
        "• Payment terms to be agreed upon order confirmation",
        "• All sales are subject to our standard terms and conditions"
    ]
    
    for term in terms:
        elems.append(Paragraph(term, styles["Small"]))
    
    elems.append(Spacer(1, 10*mm))
    elems.append(Paragraph("Thank you for your interest!", styles["Center"]))
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph("This is a computer-generated quotation.", styles["Muted"]))

    # Build PDF
    doc.build(elems)
    pdf_data = buf.getvalue()
    buf.close()
    
    return pdf_data


def _reportlab_receipt_pdf(order: Order) -> bytes:
    """Generate a receipt PDF by copying the invoice template structure but with receipt-specific changes."""
    try:
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
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise RuntimeError(
            "ReportLab is required to generate PDF documents. Install it with 'pip install reportlab'.",
        ) from exc

    # Copy exact same setup from invoice template
    try:
        pdfmetrics.registerFont(TTFont("Inter", "/app/static/fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "/app/static/fonts/Inter-Bold.ttf"))
        BASE_FONT, BASE_BOLD = "Inter", "Inter-Bold"
        logger.info("Successfully loaded Inter fonts")
    except Exception as e:
        logger.warning(f"Failed to load Inter fonts: {str(e)}, using fallback")
        BASE_FONT, BASE_BOLD = "Helvetica", "Helvetica-Bold"

    # Enhanced color scheme (same as invoice)
    BRAND_COLOR = getattr(getattr(order, "company", None), "brand_color", "#1E293B") or "#1E293B"
    ACCENT_COLOR = getattr(getattr(order, "company", None), "accent_color", "#3B82F6") or "#3B82F6"
    SUCCESS_COLOR = "#10B981"
    LIGHT_GRAY = "#F8FAFC"
    MEDIUM_GRAY = "#64748B"
    DARK_GRAY = "#334155"
    
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

    # Load images (same as invoice)
    LOGO_PATH = getattr(settings, "COMPANY_LOGO_PATH", None)
    LOGO_URL = getattr(settings, "COMPANY_LOGO_URL", None) or DEFAULT_LOGO_URL
    logo_reader = _image_reader(LOGO_PATH, LOGO_URL)

    # Same styles as invoice
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 12
    styles["Title"].fontName = BASE_BOLD

    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=11, textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Center", parent=styles["Normal"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Muted", parent=styles["Small"], textColor=MEDIUM_GRAY))
    styles.add(ParagraphStyle(name="H1", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=24, leading=28, textColor=BRAND_COLOR))
    styles.add(ParagraphStyle(name="H2", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=16, leading=20, textColor=DARK_GRAY))
    styles.add(ParagraphStyle(name="H3", parent=styles["Normal"], fontName=BASE_BOLD, fontSize=12, leading=14, textColor=DARK_GRAY))

    # Document setup (same as invoice)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"Receipt {order.code}",
        author="AA Alive Sdn. Bhd."
    )

    elems = []

    # Header with logo (same as invoice)
    if logo_reader:
        try:
            elems.append(Image(logo_reader, width=60*mm, height=30*mm, hAlign="LEFT"))
            elems.append(Spacer(1, 10*mm))
        except Exception as e:
            logger.warning(f"Failed to add logo to receipt: {str(e)}")

    # Title - CHANGED to RECEIPT
    elems.append(Paragraph("RECEIPT", styles["H1"]))
    elems.append(Spacer(1, 10*mm))

    # Company and customer info (copied from invoice template structure)
    info_data = [
        ["From:", "To:", "Receipt Details:"],
        ["AA Alive Sdn. Bhd.", getattr(order, 'customer_name', None) or getattr(order.customer, 'name', 'N/A'), f"Receipt #: {order.code}"],
        ["Kuala Lumpur, Malaysia", getattr(order, 'customer_phone', None) or getattr(order.customer, 'phone', ''), f"Date: {order.created_at.strftime('%Y-%m-%d') if hasattr(order.created_at, 'strftime') else str(order.created_at)}"],
        ["Phone: +60 12-345-6789", "", f"Order #: {order.code}"],
        ["Email: hello@aalyx.com", "", "PAID"],
    ]
    
    customer_address = getattr(order, 'delivery_address', None) or getattr(order, 'customer_address', None)
    if hasattr(order, 'customer') and hasattr(order.customer, 'address'):
        customer_address = order.customer.address
    if customer_address:
        info_data[2][1] = customer_address

    info_table = Table(info_data, colWidths=[60*mm, 60*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), BASE_FONT),
        ("FONTNAME", (2, -1), (2, -1), BASE_BOLD),  # Make PAID bold
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TEXTCOLOR", (2, -1), (2, -1), HexColor(SUCCESS_COLOR)),  # Make PAID green
    ]))
    elems.append(info_table)
    elems.append(Spacer(1, 8*mm))

    # Items table (copied from invoice logic)
    if hasattr(order, 'items') and order.items:
        # Calculate totals
        total_before_charges = sum(float(getattr(item, 'line_total', 0) or 0) for item in order.items)
        delivery_fee = float(getattr(order, 'delivery_fee', 0) or 0)
        return_delivery_fee = float(getattr(order, 'return_delivery_fee', 0) or 0)
        grand_total = total_before_charges + delivery_fee + return_delivery_fee

        item_data = [["Description", "Type", "Qty", "Unit Price", "Amount"]]
        
        for item in order.items:
            qty_str = _fmt_qty(getattr(item, 'qty', 0))
            unit_price = float(getattr(item, 'unit_price', 0) or 0)
            line_total = float(getattr(item, 'line_total', 0) or 0)
            
            item_data.append([
                getattr(item, 'name', 'Item') or 'Item',
                getattr(item, 'item_type', 'OUTRIGHT'),
                qty_str,
                money(unit_price),
                money(line_total),
            ])

        # Add charges
        if delivery_fee > 0:
            item_data.append(["Delivery Fee", "SERVICE", "1", money(delivery_fee), money(delivery_fee)])
        if return_delivery_fee > 0:
            item_data.append(["Return Delivery Fee", "SERVICE", "1", money(return_delivery_fee), money(return_delivery_fee)])

        # Totals
        item_data.append(["", "", "", "SUBTOTAL:", money(total_before_charges)])
        if delivery_fee > 0 or return_delivery_fee > 0:
            item_data.append(["", "", "", "CHARGES:", money(delivery_fee + return_delivery_fee)])
        item_data.append(["", "", "", "TOTAL PAID:", money(grand_total)])

        # Table styling (same as invoice)
        item_table = Table(item_data, colWidths=[75*mm, 25*mm, 20*mm, 25*mm, 25*mm])
        item_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), BASE_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTNAME", (0, 1), (-1, -4), BASE_FONT),
            ("FONTNAME", (0, -3), (-1, -1), BASE_BOLD),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -4), 0.5, colors.lightgrey),
            ("LINEABOVE", (0, -3), (-1, -3), 1, colors.black),
            ("LINEABOVE", (0, -1), (-1, -1), 2, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(ACCENT_COLOR)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), HexColor("#E8F5E8")),  # Light green for paid
            ("TEXTCOLOR", (0, -1), (-1, -1), HexColor(SUCCESS_COLOR)),  # Green text for paid
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elems.append(item_table)
        elems.append(Spacer(1, 8*mm))

    # Payment information
    elems.append(Paragraph("Payment Information:", styles["H3"]))
    payment_info = [
        ["Payment Status:", "PAID IN FULL"],
        ["Payment Method:", "Cash/Bank Transfer"],
        ["Transaction Date:", order.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(order.created_at, 'strftime') else str(order.created_at)],
    ]
    
    payment_table = Table(payment_info, colWidths=[50*mm, 120*mm])
    payment_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTNAME", (1, 0), (1, 0), BASE_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F0F9FF")),
        ("TEXTCOLOR", (1, 0), (1, 0), HexColor(SUCCESS_COLOR)),
    ]))
    elems.append(payment_table)
    elems.append(Spacer(1, 8*mm))

    # Notes
    if hasattr(order, 'notes') and order.notes:
        elems.append(Paragraph("Notes:", styles["H3"]))
        elems.append(Paragraph(order.notes, styles["Normal"]))
        elems.append(Spacer(1, 6*mm))

    # Receipt footer
    elems.append(Spacer(1, 10*mm))
    elems.append(Paragraph("Thank you for your business!", styles["Center"]))
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph("This is a computer-generated receipt.", styles["Muted"]))
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph("Please retain this receipt for your records.", styles["Muted"]))

    # Build PDF
    doc.build(elems)
    pdf_data = buf.getvalue()
    buf.close()
    
    logger.info(f"Generated receipt PDF ({len(pdf_data)} bytes)")
    return pdf_data
