from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..services.parser import parse_whatsapp_text
from ..services.ordersvc import create_order_from_parsed
from ..schemas import OrderOut

router = APIRouter(prefix="/parse", tags=["parse"])
log = logging.getLogger("parse")

class ParseIn(BaseModel):
    text: str | None = None
    message: str | None = None
    content: str | None = None
    body: str | None = None
    create: bool = False

def _pick_text(payload: ParseIn) -> str:
    return payload.text or payload.message or payload.content or payload.body or ""

def _extract_delivery_token(s: str) -> str | None:
    m = re.search(r"(?:deliver|delivery|hantar|antar)\s*[:\-]?\s*(\d{1,2}[\/\-\.\s]\d{1,2}(?:[\/\-\.\s]\d{2,4})?)", s, flags=re.I)
    if m: return m.group(1)
    m2 = re.search(r"\b(\d{1,2}[\/\-\.\s]\d{1,2}(?:[\/\-\.\s]\d{2,4})?)\b", s)
    return m2.group(1) if m2 else None

def _normalize_date_token(tok: str | None) -> str | None:
    if not tok: return None
    s = tok.strip().replace(".", "/").replace(" ", "/").replace("-", "/")
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", s)
    if not m:
        try:
            return datetime.fromisoformat(tok).date().isoformat()
        except Exception:
            return None
    d, mth = int(m.group(1)), int(m.group(2))
    y = int(m.group(3)) + (2000 if m.group(3) and int(m.group(3)) < 100 else 0) if m.group(3) else datetime.utcnow().year
    try:
        return datetime(y, mth, d).date().isoformat()
    except ValueError:
        return None

def _post_normalize(parsed: Dict[str, Any], original_text: str) -> Dict[str, Any]:
    parsed = dict(parsed or {})
    cust = parsed.setdefault("customer", {})
    order = parsed.setdefault("order", {})

    if not order.get("type"):
        if re.search(r"\bRM\s*[\d.,]+\s*[xX]\s*\d+\b", original_text):
            order["type"] = "INSTALLMENT"
        elif re.search(r"\bsewa\b", original_text, flags=re.I):
            order["type"] = "RENTAL"
        elif re.search(r"\bbeli\b", original_text, flags=re.I):
            order["type"] = "OUTRIGHT"

    if not order.get("code"):
        first_line = next((ln.strip() for ln in original_text.splitlines() if ln.strip()), "")
        m_code = re.search(r"([A-Z]{2,}\d{3,})", first_line)
        if m_code:
            order["code"] = m_code.group(1)

    tok = order.get("delivery_date") or _extract_delivery_token(original_text)
    iso = _normalize_date_token(tok)
    if iso:
        order["delivery_date"] = iso

    plan = order.setdefault("plan", {})
    if "type" in plan and "plan_type" not in plan:
        plan["plan_type"] = plan.pop("type")

    order.setdefault("charges", {})
    order.setdefault("items", [])
    order.setdefault("totals", {})

    if not (cust.get("name") and str(cust["name"]).strip()):
        m_name = re.search(r"(?:nama|name)\s*[:：]\s*(.+)", original_text, flags=re.I)
        cust["name"] = (m_name.group(1).strip() if m_name else "Unknown")

    return parsed

@router.post("", response_model=dict)
def parse_message(body: ParseIn, db: Session = Depends(get_session)):
    txt = _pick_text(body)
    if not txt.strip():
        raise HTTPException(400, "Missing message text. Use 'text' (or 'message'/'content'/'body').")

    try:
        parsed = parse_whatsapp_text(txt)
        parsed = _post_normalize(parsed, txt)
    except Exception as e:
        log.exception("parse error")
        raise HTTPException(400, f"Parse failed: {e}")

    if not parsed.get("order", {}).get("type"):
        raise HTTPException(400, "Parsed order type missing (OUTRIGHT|INSTALLMENT|RENTAL).")

    if not body.create:
        return {"ok": True, "parsed": parsed}

    try:
        obj = create_order_from_parsed(db, parsed)
    except Exception as e:
        raise HTTPException(400, f"Create failed: {e}")

    return {"ok": True, "created": OrderOut.model_validate(obj).model_dump()}
