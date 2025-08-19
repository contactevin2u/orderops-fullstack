from __future__ import annotations

from typing import Any, Dict, Optional, List
from datetime import datetime, date
from decimal import Decimal
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..services.parser import parse_whatsapp_text
from ..services.ordersvc import create_order_from_parsed

router = APIRouter(prefix="/parse", tags=["parse"])

RM = r"(?:RM|\$|MYR)\s*"
NUM = r"(\d+(?:[.,]\d{1,2})?)"

class ParseIn(BaseModel):
    text: str
    create: bool = False

def _coerce_decimal(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"))
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")

def _guess_code(txt: str) -> Optional[str]:
    # Prefer codes like KP2010, WC2009 etc.
    m = re.search(r"\b([A-Z]{1,3}\d{3,8})\b", txt)
    return m.group(1).strip() if m else None

def _parse_date_like(txt: str) -> Optional[str]:
    # handles 17/8, 17-08, Deliver 28/8, delivery 19/8
    m = re.search(r"(?i)\b(?:deliver(?:y)?|return|pickup|collect)?\s*([0-3]?\d)[/.-]([01]?\d)(?:[/.-](\d{2,4}))?\b", txt)
    if not m:
        return None
    d = int(m.group(1))
    mth = int(m.group(2))
    y = int(m.group(3)) if m.group(3) else datetime.utcnow().year
    if y and y < 100:
        y = 2000 + y
    try:
        dt = date(y, mth, d)
    except ValueError:
        return None
    return dt.isoformat()

_DELIVERY_KEYWORDS = (
    "penghantaran", "pasang", "pemasangan", "delivery", "hantar",
    "return trip", "return", "pickup", "ambik", "ambil"
)

def _post_normalize(parsed: Dict[str, Any], original_text: str) -> Dict[str, Any]:
    """
    Make the parser output robust:
    - Ensure required containers exist.
    - Fix common misclassifications (delivery as item, (Beli) as monthly, etc.).
    - Infer order.type and plan when possible.
    - Compute derived totals safely with Decimals.
    """
    parsed = dict(parsed or {})
    cust = parsed.setdefault("customer", {})
    order = parsed.setdefault("order", {})

    # Ensure nested structures
    items: List[Dict[str, Any]] = order.get("items") or []
    order["items"] = items
    charges: Dict[str, Any] = order.get("charges") or {}
    order["charges"] = charges
    plan: Dict[str, Any] = order.get("plan") or {}
    order["plan"] = plan
    totals: Dict[str, Any] = order.get("totals") or {}
    order["totals"] = totals

    # Fill obvious fields
    if not order.get("code"):
        code_guess = _guess_code(original_text)
        if code_guess:
            order["code"] = code_guess

    if not order.get("delivery_date"):
        maybe = _parse_date_like(original_text)
        if maybe:
            order["delivery_date"] = maybe

    # Guess type from text patterns if missing
    txt_lower = original_text.lower()
    if not order.get("type"):
        if re.search(rf"{RM}{NUM}\s*[x×]\s*\d+", original_text, flags=re.I):
            order["type"] = "INSTALLMENT"
        elif "sewa" in txt_lower or re.search(rf"{RM}{NUM}\s*/\s*(bulan|month)", txt_lower, flags=re.I):
            order["type"] = "RENTAL"
        else:
            order["type"] = "OUTRIGHT"

    # Normalize items & charges
    delivery_fee = _coerce_decimal(charges.get("delivery_fee"))
    return_delivery_fee = _coerce_decimal(charges.get("return_delivery_fee"))
    penalty_fee = _coerce_decimal(charges.get("penalty_fee"))
    discount = _coerce_decimal(charges.get("discount"))

    normalized_items: List[Dict[str, Any]] = []
    monthly_amount = Decimal("0.00")

    for it in items:
        name = (it.get("name") or "").strip()
        qty = int(it.get("qty") or 1)
        name_lower = name.lower()

        mm = it.get("monthly_amount")
        up = it.get("unit_price")

        # Delivery lines parsed as items -> convert to charges
        if any(kw in name_lower for kw in _DELIVERY_KEYWORDS):
            amt = _coerce_decimal(up if up is not None else mm)
            delivery_fee += amt
            continue

        # "(Beli)" means outright one-time purchase
        if "(beli)" in name_lower:
            price = _coerce_decimal(up if up is not None else mm)
            normalized_items.append({
                "name": re.sub(r"\s*\(beli\)\s*", "", name, flags=re.I).strip(),
                "sku": it.get("sku") or None,
                "qty": qty,
                "unit_price": price,
                "line_total": (price * qty).quantize(Decimal("0.01")),
                "category": it.get("category") or None,
                "item_type": "OUTRIGHT",
            })
            continue

        # Rental/Installment items
        if order["type"] in ("RENTAL", "INSTALLMENT"):
            value = _coerce_decimal(mm if mm is not None else up)
            if value > 0 and monthly_amount == Decimal("0.00"):
                monthly_amount = value

            normalized_items.append({
                "name": name,
                "sku": it.get("sku") or None,
                "qty": qty,
                "unit_price": _coerce_decimal(up),
                "line_total": _coerce_decimal(it.get("line_total")),
                "category": it.get("category") or None,
                "item_type": order["type"],
            })
            continue

        # Default: outright
        price = _coerce_decimal(up if up is not None else it.get("line_total"))
        normalized_items.append({
            "name": name,
            "sku": it.get("sku") or None,
            "qty": qty,
            "unit_price": price,
            "line_total": (price * qty).quantize(Decimal("0.01")),
            "category": it.get("category") or None,
            "item_type": "OUTRIGHT",
        })

    order["items"] = normalized_items

    # Build plan for rental/installment
    if order["type"] == "RENTAL":
        plan.setdefault("plan_type", "RENTAL")
        plan.setdefault("monthly_amount", monthly_amount)
        plan.setdefault("months", None)
        plan.setdefault("start_date", order.get("delivery_date"))

    elif order["type"] == "INSTALLMENT":
        plan.setdefault("plan_type", "INSTALLMENT")
        # Try detect "RM 550 X 6"
        mx = re.search(rf"{RM}{NUM}\s*[x×]\s*(\d+)", original_text, flags=re.I)
        if mx:
            plan.setdefault("monthly_amount", _coerce_decimal(mx.group(1)))
            # if months part present
            if mx.lastindex and mx.lastindex >= 2:
                plan.setdefault("months", int(mx.group(2)))
        else:
            plan.setdefault("monthly_amount", monthly_amount)
        plan.setdefault("start_date", order.get("delivery_date"))

    # Totals: upfront = first month + delivery + outright items - discount + penalties/returns
    outright_sum = sum((_coerce_decimal(i.get("unit_price")) * int(i.get("qty") or 1)) for i in normalized_items if i.get("item_type") == "OUTRIGHT")
    upfront_month = monthly_amount if order["type"] in ("RENTAL", "INSTALLMENT") else Decimal("0.00")

    subtotal = (outright_sum + upfront_month).quantize(Decimal("0.01"))
    total = (subtotal + delivery_fee + return_delivery_fee + penalty_fee - discount).quantize(Decimal("0.01"))
    paid = _coerce_decimal(order.get("totals", {}).get("paid"))
    to_collect = (total - paid).quantize(Decimal("0.01"))

    charges["delivery_fee"] = delivery_fee
    charges["return_delivery_fee"] = return_delivery_fee
    charges["penalty_fee"] = penalty_fee
    charges["discount"] = discount

    order["charges"] = charges
    order["plan"] = plan
    order["totals"] = {
        "subtotal": subtotal,
        "total": total,
        "paid": paid,
        "to_collect": to_collect,
    }

    # Minimal customer cleanup
    if cust.get("phone"):
        cust["phone"] = str(cust["phone"]).strip()

    return parsed

@router.post("", response_model=Dict[str, Any])
def parse_message(body: ParseIn, db: Session = Depends(get_session)):
    txt = (body.text or "").strip()
    if not txt:
        raise HTTPException(400, "Missing message text. Use 'text'.")

    try:
        parsed = parse_whatsapp_text(txt)
        parsed = _post_normalize(parsed, txt)
    except Exception as e:
        raise HTTPException(400, f"Parse failed: {e}")

    if not parsed.get("order", {}).get("type"):
        raise HTTPException(400, "Parsed order type missing (OUTRIGHT|INSTALLMENT|RENTAL).")

    if not body.create:
        return parsed

    # create == True
    created = create_order_from_parsed(db, parsed)
    return created
