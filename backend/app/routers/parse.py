from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
# IMPORTANT: the real parser lives in services/parser.py as `parse_whatsapp_text`.
# To avoid another mismatch, we alias it as parse_text here.
from ..services.parser import parse_whatsapp_text as parse_text
from ..services.ordersvc import create_from_parsed, _apply_charges_and_totals
from ..utils.dates import parse_relaxed_date
from ..utils.normalize import ensure_dict, ensure_list, to_decimal
from ..models.order import Order
from ..utils.responses import envelope

router = APIRouter(prefix="/parse", tags=["parse"])


class ParseIn(BaseModel):
    text: str
    create_order: bool = False


def _post_normalize(parsed: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """
    Make the parser output safe for order creation:
    - default missing objects
    - coerce numerics to Decimal
    - infer plan_type from order.type when absent
    """
    parsed = ensure_dict(parsed)
    customer = ensure_dict(parsed.get("customer"))
    order = ensure_dict(parsed.get("order"))

    # Charges (initial values before item cleanup)
    ch = ensure_dict(order.get("charges"))
    delivery_fee = to_decimal(ch.get("delivery_fee"))
    return_delivery_fee = to_decimal(ch.get("return_delivery_fee"))
    penalty_fee = to_decimal(ch.get("penalty_fee"))
    discount = to_decimal(ch.get("discount"))

    def _is_delivery_item(name: str) -> bool:
        n = name.lower()
        keywords = (
            "delivery",
            "penghantaran",
            "pasang",
            "installation",
            "instalasi",
            "pickup",
            "collect",
            "waive",
            "percuma",
        )
        return any(k in n for k in keywords)

    # Items
    items = []
    for it in ensure_list(order.get("items")):
        it = ensure_dict(it)
        qty = to_decimal(it.get("qty") or 1).quantize(Decimal("1"))
        unit_price = to_decimal(it.get("unit_price"))
        line_total = to_decimal(it.get("line_total"))
        monthly_amount = to_decimal(it.get("monthly_amount"))
        item_type = (it.get("item_type") or order.get("type") or "").upper() or "OUTRIGHT"
        name = it.get("name") or "Item"

        # If instalment/rental line without price, treat monthly_amount as line total
        if item_type in {"INSTALLMENT", "RENTAL"} and line_total == Decimal("0.00") and monthly_amount > 0:
            unit_price = monthly_amount
            line_total = monthly_amount

        if _is_delivery_item(name):
            if delivery_fee == Decimal("0.00"):
                delivery_fee = line_total
            # Skip adding this item as it's treated as a delivery fee
            continue

        items.append({
            "name": name,
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
    plan = ensure_dict(order.get("plan"))
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

    order["charges"] = {
        "delivery_fee": delivery_fee,
        "return_delivery_fee": return_delivery_fee,
        "penalty_fee": penalty_fee,
        "discount": discount,
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


    o = parsed.get("order", {}) or {}
    sub, disc, df, rdf, pf, tot, paid = _apply_charges_and_totals(
        o.get("items") or [], o.get("charges") or {}, o.get("totals") or {}
    )
    o["totals"] = {
        "subtotal": sub,
        "total": tot,
        "paid": paid,
        "to_collect": (tot - paid),
    }
    parsed["order"] = o
    created: dict = {}
    if body.create_order:
        idem_key = hashlib.sha1(raw.encode()).hexdigest()
        existing = db.query(Order).filter(Order.idempotency_key == idem_key).one_or_none()
        if existing:
            created = {"order_id": existing.id, "code": existing.code}
        else:
            try:
                order = create_from_parsed(db, parsed, idem_key)
                created = {"order_id": order.id, "code": order.code}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(400, f"could not create order: {e}")

    return envelope(
        {
            "parsed": _jsonify_for_frontend(parsed),
            **({"created": created} if created else {}),
        }
    )
