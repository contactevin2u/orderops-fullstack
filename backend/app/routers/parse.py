from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from ..db import get_session
from ..services import ordersvc
from ..services.parser import parse_text  # your existing LLM/regex parser

router = APIRouter(prefix="/parse", tags=["parse"])

class ParseIn(BaseModel):
    text: str
    create: bool | None = False

class ParseOut(BaseModel):
    ok: bool
    parsed: dict | None = None
    order_id: int | None = None
    message: str | None = None

NUM0 = Decimal("0.00")

def _to_decimal(x) -> Decimal:
    if x is None:
        return NUM0
    if isinstance(x, Decimal):
        return x
    try:
        # Accept ints/floats/strings safely
        return Decimal(str(x).strip().replace(",", ""))
    except (InvalidOperation, AttributeError):
        return NUM0

def _ensure_dict(d):
    return d if isinstance(d, dict) else {}

def _extract_code_if_missing(raw_text: str) -> str | None:
    # Examples: KP2010, Kp2017, WC2009, etc.
    m = re.search(r"\b([A-Za-z]{1,3}\d{3,6})\b", raw_text)
    return m.group(1).upper() if m else None

def _normalize_datestr(s: str | None) -> str | None:
    if not s:
        return None
    # Accept things like "delivery 19/8", "19/8", "17/08", "17/8 before 9pm"
    mm = re.search(r"(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?", s)
    if not mm:
        return s
    d, m, y = mm.group(1), mm.group(2), mm.group(3)
    now = datetime.now()
    year = int(y) if y else now.year
    try:
        dt = datetime(year=int(year), month=int(m), day=int(d))
        return dt.date().isoformat()
    except ValueError:
        return s

def _post_normalize(parsed: dict, raw_text: str) -> dict:
    if not isinstance(parsed, dict):
        parsed = {}

    customer = _ensure_dict(parsed.get("customer"))
    order = _ensure_dict(parsed.get("order"))

    # --- plan safe dict
    plan = _ensure_dict(order.get("plan"))
    # If someone put plan fields at root of order, still OK.
    if not plan and ("months" in order or "monthly_amount" in order):
        plan = {"months": order.get("months"), "monthly_amount": order.get("monthly_amount")}
    order["plan"] = plan

    # --- charges & totals normalization
    charges = _ensure_dict(order.get("charges"))
    totals = _ensure_dict(order.get("totals"))

    # Some models accidentally put totals under charges
    # Promote if present & totals empty
    for k in ("total", "paid", "to_collect", "subtotal"):
        if k in charges and k not in totals:
            totals[k] = charges.pop(k)

    # Ensure numeric shapes
    for key in ("subtotal", "total", "paid", "to_collect"):
        totals[key] = float(_to_decimal(totals.get(key)))

    for key in ("delivery_fee", "return_delivery_fee", "penalty_fee", "discount"):
        charges[key] = float(_to_decimal(charges.get(key)))

    order["charges"] = charges
    order["totals"] = totals

    # --- delivery date normalization
    order["delivery_date"] = _normalize_datestr(order.get("delivery_date"))

    # --- type & plan_type sanity
    otype = (order.get("type") or "").upper()
    if otype not in ("OUTRIGHT", "INSTALLMENT", "RENTAL"):
        # derive from raw text hints
        if re.search(r"\b(ANSURAN|INSTALLMENT)\b", raw_text, re.I):
            otype = "INSTALLMENT"
        elif re.search(r"\b(SEWA|RENTAL)\b", raw_text, re.I):
            otype = "RENTAL"
        else:
            otype = "OUTRIGHT"
    order["type"] = otype

    if "plan_type" not in plan and otype in ("INSTALLMENT", "RENTAL"):
        plan["plan_type"] = otype

    # months / monthly_amount can be text – coerce to numbers
    plan["months"] = int(plan.get("months") or 0)
    plan["monthly_amount"] = float(_to_decimal(plan.get("monthly_amount")))

    # --- items normalization
    items = order.get("items") or []
    norm_items = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = (it.get("name") or "").strip() or "Item"
        qty = int(it.get("qty") or 1)
        item_type = (it.get("item_type") or "").upper()
        monthly_amount = float(_to_decimal(it.get("monthly_amount")))
        unit_price = float(_to_decimal(it.get("unit_price")))
        line_total = float(_to_decimal(it.get("line_total")))
        # Fix common mislabels:
        # - If monthly_amount > 0, it's recurring (match order type)
        if monthly_amount > 0 and otype in ("INSTALLMENT", "RENTAL"):
            item_type = otype
            # keep unit_price as monthly for record
            if unit_price == 0:
                unit_price = monthly_amount
            if line_total == 0:
                line_total = monthly_amount * qty
        # - If name contains "(Beli)" or looks like outright and there's a single number with no '/bulan'
        if re.search(r"\(beli\)", name, re.I) and item_type in ("", "INSTALLMENT", "RENTAL"):
            item_type = "OUTRIGHT"

        norm_items.append({
            "name": name,
            "sku": it.get("sku"),
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total if line_total else unit_price * qty,
            "category": it.get("category"),
            "item_type": item_type or ("OUTRIGHT" if otype == "OUTRIGHT" else otype),
            "monthly_amount": monthly_amount,
        })

    order["items"] = norm_items

    # --- code normalization / fallback
    code = (order.get("code") or "").strip()
    if not code:
        code = _extract_code_if_missing(raw_text) or ""
    order["code"] = code.upper() if code else ""

    parsed["customer"] = customer
    parsed["order"] = order
    return parsed

@router.post("", response_model=ParseOut)
def parse_message(body: ParseIn, db: Session = Depends(get_session)):
    """
    1) Parse raw WhatsApp text to structured order
    2) Normalize & fix common shape/typing issues
    3) Optionally create the order in DB (unique code, totals computed)
    """
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")

    try:
        raw = parse_text(text)  # your existing parser (LLM or rules)
    except Exception as e:
        raise HTTPException(500, f"Parser error: {e}")

    try:
        parsed = _post_normalize(raw, text)
    except Exception as e:
        # Make absolutely sure parse endpoint never 500s on shape issues
        raise HTTPException(400, f"normalize error: {e}")

    if not body.create:
        return ParseOut(ok=True, parsed=parsed, order_id=None, message="Parsed only")

    # Create in DB safely
    try:
        created = ordersvc.create_from_parsed(db=db, parsed=parsed)
        return ParseOut(ok=True, parsed=parsed, order_id=created.id, message="Order created")
    except HTTPException:
        raise
    except Exception as e:
        # Return as 400 to surface problems but not crash worker
        raise HTTPException(400, f"create error: {e}")
