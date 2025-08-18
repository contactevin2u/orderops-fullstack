from __future__ import annotations
from typing import Any, Dict
import os, json, re
from datetime import datetime
from ..core.config import settings

# OpenAI client (lazy import to avoid hard dependency if key missing)
def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)

SCHEMA = {
  "type": "object",
  "properties": {
    "customer": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "phone": {"type": "string"},
        "address": {"type": "string"},
        "map_url": {"type": "string"}
      },
      "required": ["name"]
    },
    "order": {
      "type": "object",
      "properties": {
        "type": {"type": "string", "enum": ["OUTRIGHT","INSTALLMENT","RENTAL"]},
        "code": {"type": "string"},
        "delivery_date": {"type": "string"},
        "notes": {"type": "string"},
        "items": {"type": "array"},
        "charges": {"type": "object"},
        "plan": {"type": "object"},
        "totals": {"type": "object"}
      },
      "required": ["type"]
    }
  },
  "required": ["customer","order"]
}

SYSTEM = """You are a robust parser that outputs ONLY JSON that strictly conforms to a provided JSON Schema. 
- Interpret Malaysian order messages for medical equipment sales/rentals.
- If a line like RM <amount> x <months> exists, set order.type=INSTALLMENT and plan = {months, monthly_amount}.
- If 'Sewa' is present and no x <months>, set type=RENTAL.
- If 'Beli' and no x <months>, set type=OUTRIGHT.
- Try to capture 'code' if the first line contains a token like WC2009 (letters+digits).
- delivery_date can be DD/MM or DD-MM or 'Deliver 28/8'. Keep as provided string (do not reformat).
- Keep monetary numbers as numbers (no currency text) with 2 decimals where applicable.
- Do not hallucinate fields you cannot infer."""

def _heuristic_fallback(text: str) -> Dict[str, Any]:
    def rm2f(s: str) -> float:
        try:
            return float(s.replace(',', '').strip())
        except Exception:
            return 0.0

    # Guess type
    t = "OUTRIGHT"
    if re.search(r"sewa", text, flags=re.I):
        t = "RENTAL"
    if re.search(r"\bRM\s*[\d.,]+\s*[xX]\s*\d+\b", text):
        t = "INSTALLMENT"

    # Delivery date
    m_delivery = re.search(r"(?:deliver|delivery|hantar|antar)\s*(\d{1,2}[/\-]\d{1,2})", text, flags=re.I)
    delivery = m_delivery.group(1) if m_delivery else ""

    # Names & phone/address (rough)
    m_name = re.search(r"(?:nama|name)\s*[:：]\s*(.+)", text, flags=re.I)
    m_phone = re.search(r"(?:\+?6?01\d[\d\-\s]{6,})", text)
    m_addr = re.search(r"(?:📌|alamat|address)\s*[:：]?\s*(.+)", text, flags=re.I)

    # Code on first line like WC2009
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m_code = re.search(r"([A-Z]{2,}\d{3,})", first_line)

    # Installment pattern
    m_inst = re.search(r"RM\s*([\d.,]+)\s*[xX]\s*(\d+)", text)
    plan = {}
    if t == "INSTALLMENT" and m_inst:
        monthly = rm2f(m_inst.group(1))
        months = int(m_inst.group(2))
        plan = {"type": "INSTALLMENT", "months": months, "monthly_amount": monthly}

    # Delivery fee
    m_deliv_fee = re.search(r"(?:penghantaran|delivery)[^\d]*RM\s*([\d.,]+)", text, flags=re.I)

    # Totals
    m_total = re.search(r"total\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)
    m_paid = re.search(r"paid\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)
    m_collect = re.search(r"(?:to\s*collect|balance)\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)

    data = {
        "customer": {
            "name": (m_name.group(1).strip() if m_name else ""),
            "phone": (m_phone.group(0).strip() if m_phone else ""),
            "address": (m_addr.group(1).strip() if m_addr else ""),
            "map_url": ""
        },
        "order": {
            "type": t,
            "code": m_code.group(1) if m_code else "",
            "delivery_date": delivery,
            "notes": "",
            "items": [],
            "charges": {
                "delivery_fee": rm2f(m_deliv_fee.group(1)) if m_deliv_fee else 0,
                "return_delivery_fee": 0,
                "penalty_fee": 0,
                "discount": 0
            },
            "plan": plan,
            "totals": {
                "subtotal": rm2f(m_total.group(1)) if m_total else 0,
                "total": rm2f(m_total.group(1)) if m_total else 0,
                "paid": rm2f(m_paid.group(1)) if m_paid else 0,
                "to_collect": rm2f(m_collect.group(1)) if m_collect else 0
            }
        }
    }
    return data

def parse_whatsapp_text(text: str) -> Dict[str, Any]:
    # If real parse is enabled, try OpenAI with strict schema
    if settings.FEATURE_PARSE_REAL and settings.OPENAI_API_KEY:
        client = _openai_client()
        schema_str = json.dumps(SCHEMA)
        messages = [
            {"role": "system", "content": SYSTEM + " Output must be valid JSON only."},
            {"role": "user", "content": "Schema:\n" + schema_str},
            {"role": "user", "content": "Parse this message into the schema:\n" + text}
        ]
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=messages
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
        except Exception:
            data = _heuristic_fallback(text)
    else:
        data = _heuristic_fallback(text)

    # --- Post-normalization: ensure code & installment hints are captured ---
    # Code on first line
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m_code = re.search(r"([A-Z]{2,}\d{3,})", first_line)
    if m_code:
        data.setdefault("order", {})["code"] = m_code.group(1)

    # Installment pattern
    m_inst = re.search(r"RM\s*([\d.,]+)\s*[xX]\s*(\d+)", text)
    if m_inst:
        monthly = float(m_inst.group(1).replace(',', ''))
        months = int(m_inst.group(2))
        order = data.setdefault("order", {})
        order["type"] = "INSTALLMENT"
        plan = order.setdefault("plan", {})
        plan.update({"type": "INSTALLMENT", "months": months, "monthly_amount": monthly})

    return data
