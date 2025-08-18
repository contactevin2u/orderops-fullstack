from typing import Any, Dict
import os, json, re
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
        "delivery_date": {"type": "string"},
        "notes": {"type": "string"},
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "sku": {"type": "string"},
              "category": {"type": "string"},
              "item_type": {"type": "string", "enum": ["OUTRIGHT","INSTALLMENT","RENTAL","FEE"]},
              "qty": {"type": "number"},
              "unit_price": {"type": "number"},
              "line_total": {"type": "number"}
            },
            "required": ["name","item_type"]
          }
        },
        "charges": {
          "type": "object",
          "properties": {
            "delivery_fee": {"type": "number"},
            "return_delivery_fee": {"type": "number"},
            "penalty_fee": {"type": "number"},
            "discount": {"type": "number"}
          }
        },
        "plan": {
          "type": "object",
          "properties": {
            "plan_type": {"type": "string", "enum": ["RENTAL","INSTALLMENT"]},
            "months": {"type": "number"},
            "monthly_amount": {"type": "number"},
            "start_date": {"type": "string"}
          }
        },
        "totals": {
          "type": "object",
          "properties": {
            "subtotal": {"type": "number"},
            "total": {"type": "number"},
            "paid": {"type": "number"},
            "to_collect": {"type": "number"}
          }
        }
      },
      "required": ["type","items"]
    }
  },
  "required": ["customer","order"]
}

SYSTEM = (
    "You are a strict, reliable order-intake parser for Malaysian medical equipment (hospital beds, wheelchairs, "
    "oxygen concentrators). Return ONLY valid JSON matching the schema. Currency is RM. Monthly rental/instalment "
    "has no prorate. If delivery date is specified like '(Delivery 17/8)' or '(return 17/8)', parse it as dd/mm."
)

EXAMPLES = [
"""Example:
KP1989 (Delivery 17/8) Stella Ann Konasargaran 014-9053538 No 43, lorong 5 , taman sri wangsa, 31000 batu gajah perak (Sewa) Katil 3 Function Manual - RM 250/bulanan Tilam Canvas (Beli) - RM 199 Penghantaran & Pemasangan (satu hala) - RM 280 Total - RM 729 Bulan Seterusnya - RM 250/bulanan Paid- RM0 To collect -RM729
"""
]

def parse_whatsapp_text(text: str) -> Dict[str, Any]:
    if settings.FEATURE_PARSE_REAL and settings.OPENAI_API_KEY:
        client = _openai_client()
        schema_str = json.dumps(SCHEMA)
        messages = [
            {"role":"system","content": SYSTEM + " Output must be JSON in English keys."},
            {"role":"user","content": "Schema:\n" + schema_str},
            {"role":"user","content": "Parse this message into the schema:\n" + text}
        ]
        try:
            # Using Chat Completions with JSON mode
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type":"json_object"},
                temperature=0.1,
            )
            data = resp.choices[0].message.content
            return json.loads(data)
        except Exception as e:
            # fall through to heuristic minimal parser
            pass

    # Heuristic minimal fallback (best-effort)
    phone = re.findall(r'(\+?6?0\d[\d- ]{7,})', text)
    m_total = re.search(r'Total(?: After discount)?\s*-\s*RM\s*([\d,.]+)', text, re.I)
    m_paid = re.search(r'Paid\s*-\s*RM\s*([\d,.]+)', text, re.I)
    m_collect = re.search(r'To\s*collect\s*-\s*RM\s*([\d,.]+)', text, re.I)
    m_delivery = re.search(r'Delivery\s*(\d{1,2}/\d{1,2})', text, re.I)

    def rm2f(s):
        if not s: return 0.0
        return float(str(s).replace(',',''))

    order_type = "RENTAL" if re.search(r'\(Sewa\)|bulanan', text, re.I) else ("OUTRIGHT" if re.search(r'\bBeli\b|BELI', text, re.I) else "OUTRIGHT")

    return {
        "customer": {
            "name": (re.split(r'\d{2,}', text, maxsplit=1)[0] or "Customer").strip()[:200],
            "phone": phone[0].strip() if phone else "",
            "address": "",
            "map_url": ""
        },
        "order": {
            "type": order_type,
            "delivery_date": m_delivery.group(1) if m_delivery else "",
            "notes": "",
            "items": [
                {"name":"Parsed Item","sku":"","category":"","item_type": order_type, "qty":1,"unit_price": rm2f(m_total.group(1)) if m_total else 0,"line_total": rm2f(m_total.group(1)) if m_total else 0}
            ],
            "charges": {"delivery_fee":0,"return_delivery_fee":0,"penalty_fee":0,"discount":0},
            "plan": {"plan_type":"RENTAL","months":None,"monthly_amount": rm2f(m_collect.group(1)) if (order_type=="RENTAL" and m_collect) else 0,"start_date":""},
            "totals": {"subtotal": rm2f(m_total.group(1)) if m_total else 0,"total": rm2f(m_total.group(1)) if m_total else 0,"paid": rm2f(m_paid.group(1)) if m_paid else 0,"to_collect": rm2f(m_collect.group(1)) if m_collect else 0}
        }
    }
