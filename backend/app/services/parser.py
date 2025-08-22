from __future__ import annotations

from typing import Any, Dict
import json

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
                "map_url": {"type": "string"},
            },
            "required": ["name"],
        },
        "order": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["OUTRIGHT", "INSTALLMENT", "RENTAL", "MIXED"],
                },
                "code": {"type": "string"},
                "delivery_date": {"type": "string"},
                "notes": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "qty": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "line_total": {"type": "number"},
                            "item_type": {
                                "type": "string",
                                "enum": ["OUTRIGHT", "INSTALLMENT", "RENTAL", "FEE"],
                            },
                            "monthly_amount": {"type": "number"},
                        },
                        "required": [
                            "name",
                            "qty",
                            "unit_price",
                            "line_total",
                            "item_type",
                        ],
                    },
                },
                "charges": {
                    "type": "object",
                    "properties": {
                        "delivery_fee": {"type": "number"},
                        "return_delivery_fee": {"type": "number"},
                        "penalty_fee": {"type": "number"},
                        "discount": {"type": "number"},
                    },
                },
                "plan": {
                    "type": "object",
                    "properties": {
                        "plan_type": {"type": "string"},
                        "months": {"type": "integer"},
                        "monthly_amount": {"type": "number"},
                    },
                },
                "totals": {
                    "type": "object",
                    "properties": {
                        "subtotal": {"type": "number"},
                        "total": {"type": "number"},
                        "paid": {"type": "number"},
                        "to_collect": {"type": "number"},
                    },
                },
            },
            "required": ["type"],
        },
    },
    "required": ["customer", "order"],
}


SYSTEM = """You are a robust parser that outputs ONLY JSON that strictly conforms to a provided JSON Schema.
- Interpret Malaysian order messages for medical equipment sales/rentals.
- Use each original item's line text (before any price) as the item's name.
- Emit every line describing an item under order.items and assign item_type for each line (OUTRIGHT, INSTALLMENT, RENTAL, or FEE).
- Explicitly treat any line containing words like 'Sewa' or 'Rent' as RENTAL.
- Detect instalment patterns such as 'RM 259 x 6 bulan' or 'RM80/bulanan', marking the line as INSTALLMENT and populating order.plan with months and monthly_amount.
- Each order.items entry must include name, qty, unit_price, line_total, and item_type; include monthly_amount when relevant.
- Map any 'penghantaran' or 'delivery' amounts into order.charges.delivery_fee. order.charges supports delivery_fee, return_delivery_fee, penalty_fee, and discount.
- When multiple item types are present, set order.type="MIXED"; otherwise set it to the sole item_type.
- Try to capture 'code' if the first line contains a token like WC2009 (letters+digits).
- delivery_date can be DD/MM or DD-MM or 'Deliver 28/8'. Keep as provided string (do not reformat).
- Keep monetary numbers as numbers (no currency text) with 2 decimals where applicable.
- Populate order.totals with subtotal, total, paid, and to_collect (use 0 when unknown).
- Do not hallucinate fields you cannot infer."""


def parse_whatsapp_text(text: str) -> Dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = _openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "order", "schema": SCHEMA, "strict": True},
        },
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
    )
    msg = resp.choices[0].message
    raw = getattr(msg, "content", None) or getattr(msg, "parsed", "{}")
    if isinstance(raw, dict):
        return raw
    return json.loads(raw or "{}")

