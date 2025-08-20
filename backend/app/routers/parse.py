from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
# IMPORTANT: the real parser lives in services/parser.py as `parse_whatsapp_text`.
# To avoid another mismatch, we alias it as parse_text here.
from ..services.parser import parse_whatsapp_text as parse_text
from ..services.ordersvc import create_from_parsed
from ..utils.dates import parse_relaxed_date

router = APIRouter(prefix="/parse", tags=["parse"])


class ParseIn(BaseModel):
    text: str
    create_order: bool = False


def _d(val: Any) -> Decimal:
    """Decimal with 2dp, tolerant of None/str/float/int."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _ensure_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _ensure_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _post_normalize(parsed: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """
    Make the parser output safe for order creation:
    - default missing objects
    - coerce numerics to Decimal
    - infer plan_type from order.type when absent
    - compute totals when missing or zero-ish
    """
    parsed = _ensure_dict(parsed)
    customer = _ensure_dict(parsed.get("customer"))
    order = _ensure_dict(parsed.get("order"))

    # Items
    items = []
    for it in _ensure_list(order.get("items")):
        it = _ensure_dict(it)
        qty = _d(it.get("qty") or 1).quantize(Decimal("1"))
        unit_price = _d(it.get("unit_price"))
        line_total = _d(it.get("line_total"))
        monthly_amount = _d(it.get("monthly_amount"))
        item_type = (it.get("item_type") or order.get("type") or "").upper() or "OUTRIGHT"

        # If instalment/rental line without price, treat monthly_amount as line total
        if item_type in {"INSTALLMENT", "RENTAL"} and line_total == Decimal("0.00") and monthly_amount > 0:
            unit_price = monthly_amount
            line_total = monthly_amount

        items.append({
            "name": it.get("name") or "Item",
            "sku": it.get("sku") or None,
            "category": it.get("category") or None,
            "item_type": item_type,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        })
    order["items"] = items

    # Determine order.type based on item types
    item_types = {it["item_type"] for it in items if it.get("item_type") and it["item_type"] != "FEE"}
    if len(item_types) > 1:
        order["type"] = "MIXED"
    elif item_types:
        order["type"] = next(iter(item_types))

    # Normalise plan
    plan = _ensure_dict(order.get("plan"))
    if "plan_type" not in plan:
        otype = order.get("type")
        if otype in {"RENTAL", "INSTALLMENT"}:
            plan["plan_type"] = otype
        else:
            for it in items:
                if it["item_type"] in {"RENTAL", "INSTALLMENT"}:
                    plan["plan_type"] = it["item_type"]
                    break
    order["plan"] = plan

    # Try to derive delivery_date if it's a short "19/8" or embedded
    dd = str(order.get("delivery_date") or "").strip()
    d_obj = parse_relaxed_date(dd) if dd else None
    if not d_obj:
        d_obj = parse_relaxed_date(raw_text)
    order["delivery_date"] = (
        datetime(d_obj.year, d_obj.month, d_obj.day) if d_obj else None
    )

    # Charges
    ch = _ensure_dict(order.get("charges"))
    delivery_fee = _d(ch.get("delivery_fee"))
    return_delivery_fee = _d(ch.get("return_delivery_fee"))
    penalty_fee = _d(ch.get("penalty_fee"))
    discount = _d(ch.get("discount"))

    # Totals (recompute when missing/zero)
    totals = _ensure_dict(order.get("totals"))
    subtotal = _d(totals.get("subtotal"))
    total = _d(totals.get("total"))
    paid = _d(totals.get("paid"))
    to_collect = _d(totals.get("to_collect"))

    if subtotal == Decimal("0.00"):
        subtotal = sum(_d(i.get("line_total")) for i in items)

    fees = delivery_fee + return_delivery_fee + penalty_fee - discount
    computed_total = (subtotal + fees).quantize(Decimal("0.01"))
    if total == Decimal("0.00") or total != computed_total:
        total = computed_total
    if to_collect == Decimal("0.00"):
        to_collect = (total - paid).quantize(Decimal("0.01"))

    order["charges"] = {
        "delivery_fee": delivery_fee,
        "return_delivery_fee": return_delivery_fee,
        "penalty_fee": penalty_fee,
        "discount": discount,
    }
    order["totals"] = {
        "subtotal": subtotal,
        "total": total,
        "paid": paid,
        "to_collect": to_collect,
    }
    order["plan"] = plan

    parsed["customer"] = customer
    parsed["order"] = order
    return parsed


def _jsonify_for_frontend(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Front-end expects plain numbers; convert Decimals and datetimes."""
    def conv(v):
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, dict):
            return {k: conv(v) for k, v in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return conv(parsed)  # type: ignore


@router.post("", response_model=dict)
def parse_message(body: ParseIn, db: Session = Depends(get_session)):
    raw = (body.text or "").strip()
    if not raw:
        raise HTTPException(400, "text is required")

    try:
        parsed = parse_text(raw) or {}
    except Exception as e:
        # Surface a 400 so the UI can show message and still allow manual entry
        raise HTTPException(400, f"parse failed: {e}")

    parsed = _post_normalize(parsed, raw)

    created = {}
    if body.create_order:
        try:
            order_id, code = create_from_parsed(parsed, db)
            created = {"order_id": order_id, "code": code}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"could not create order: {e}")

    return {
        "ok": True,
        "parsed": _jsonify_for_frontend(parsed),
        **({"created": created} if created else {}),
    }
