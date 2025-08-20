from __future__ import annotations
from typing import Any, Dict
import os, json, re
from datetime import datetime
from ..core.config import settings

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
        "type": {"type": "string", "enum": ["OUTRIGHT","INSTALLMENT","RENTAL","MIXED"]},
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
- Use each original item's line text (before any price) as the item's name.
- Emit every line describing an item under order.items and assign item_type for each line (OUTRIGHT, INSTALLMENT, RENTAL, or FEE).
- Map any 'penghantaran' or 'delivery' amounts into order.charges.delivery_fee.
- If a line like RM <amount> x <months> exists, set that item's item_type=INSTALLMENT and plan = {months, monthly_amount, plan_type:"INSTALLMENT"}.
- If 'Sewa' is present and no x <months>, set that item's item_type=RENTAL.
- If 'Beli' and no x <months>, set that item's item_type=OUTRIGHT.
- When multiple item types are present, set order.type="MIXED"; otherwise set it to the sole item_type.
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

    t = "OUTRIGHT"
    if re.search(r"sewa", text, flags=re.I):
        t = "RENTAL"
    if re.search(r"RM\s*[\d.,]+\s*[xX]\s*\d+", text):
        t = "INSTALLMENT"

    m_delivery = re.search(r"(?:deliver|delivery|hantar|antar)\s*(\d{1,2}[/\-]\d{1,2})", text, flags=re.I)
    delivery = m_delivery.group(1) if m_delivery else ""

    m_name = re.search(r"(?:nama|name)\s*[:：]\s*(.+)", text, flags=re.I)
    m_phone = re.search(r"(?:\+?6?01\d[\d\-\s]{6,})", text)
    m_addr = re.search(r"(?:📌|alamat|address)\s*[:：]?\s*(.+)", text, flags=re.I)

    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m_code = re.search(r"([A-Z]{2,}\d{3,})", first_line)

    m_inst = re.search(r"RM\s*([\d.,]+)\s*[xX]\s*(\d+)", text)
    plan = {}
    if m_inst:
        monthly = rm2f(m_inst.group(1))
        months = int(m_inst.group(2))
        plan = {"plan_type": "INSTALLMENT", "months": months, "monthly_amount": monthly}

    m_deliv_fee = re.search(r"(?:penghantaran|delivery)[^\d]*RM\s*([\d.,]+)", text, flags=re.I)
    m_total = re.search(r"total\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)
    m_paid = re.search(r"paid\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)
    m_collect = re.search(r"(?:to\s*collect|balance)\s*[:：]?\s*RM\s*([\d.,]+)", text, flags=re.I)

    items = []
    seen_types = set()
    for line in text.splitlines():
        m_item = re.search(r"(.*)RM\s*([\d.,]+)", line, flags=re.I)
        if not m_item:
            continue
        if re.search(r"(total|deposit|paid|balance|collect|penghantaran|delivery|antar|hantar)", line, flags=re.I):
            continue
        desc = m_item.group(1).strip().strip(':- ')
        price = rm2f(m_item.group(2))
        if not desc:
            continue

        line_type = "OUTRIGHT"
        if re.search(r"RM\s*[\d.,]+\s*[xX]\s*\d+", line):
            line_type = "INSTALLMENT"
        elif re.search(r"sewa", line, flags=re.I):
            line_type = "RENTAL"
        elif re.search(r"beli", line, flags=re.I):
            line_type = "OUTRIGHT"
        seen_types.add(line_type)

        items.append({
            "name": desc,
            "qty": 1,
            "unit_price": price,
            "line_total": price,
            "item_type": line_type,
        })

    if seen_types:
        if len(seen_types) > 1:
            t = "MIXED"
        else:
            t = next(iter(seen_types))

    data = {
        "customer": {
            "name": (m_name.group(1).strip() if m_name else ""),
            "phone": (m_phone.group(0).strip() if m_phone else ""),
            "address": (m_addr.group(1).strip() if m_addr else ""),
            "map_url": "",
        },
        "order": {
            "type": t,
            "code": m_code.group(1) if m_code else "",
            "delivery_date": delivery,
            "notes": "",
            "items": items,
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
    if settings.FEATURE_PARSE_REAL and settings.OPENAI_API_KEY:
        client = _openai_client()
        try:
            resp = client.responses.create(
                model="gpt-4o-mini",
                temperature=0.1,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "OrderSchema", "schema": SCHEMA},
                },
                input=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": "Schema:\n" + json.dumps(SCHEMA)},
                    {"role": "user", "content": "Parse this message into the schema:\n" + text},
                ],
            )
            raw = getattr(resp, "output_text", "{}") or "{}"
            data = json.loads(raw)
        except Exception:
            data = _heuristic_fallback(text)
    else:
        data = _heuristic_fallback(text)

    order = data.setdefault("order", {})
    need_heur = not order.get("items")
    charges = order.setdefault("charges", {})
    if not charges.get("delivery_fee"):
        need_heur = True
    if need_heur:
        heur = _heuristic_fallback(text)
        if not order.get("items"):
            order["items"] = heur.get("order", {}).get("items", [])
        if not charges.get("delivery_fee") and heur.get("order", {}).get("charges", {}).get("delivery_fee"):
            charges["delivery_fee"] = heur["order"]["charges"]["delivery_fee"]

    # Ensure code on first line
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m_code = re.search(r"([A-Z]{2,}\d{3,})", first_line)
    if m_code:
        data.setdefault("order", {})["code"] = m_code.group(1)

    # Ensure installment hint
    m_inst = re.search(r"RM\s*([\d.,]+)\s*[xX]\s*(\d+)", text)
    if m_inst:
        monthly = float(m_inst.group(1).replace(',', ''))
        months = int(m_inst.group(2))
        order = data.setdefault("order", {})
        order["type"] = "INSTALLMENT"
        plan = order.setdefault("plan", {})
        plan.update({"plan_type": "INSTALLMENT", "months": months, "monthly_amount": monthly})

    return data
