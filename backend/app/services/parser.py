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
                "phone": {"type": ["string", "null"]},
                "address": {"type": ["string", "null"]},
                "map_url": {"type": ["string", "null"]},
            },
            "required": ["name", "phone", "address", "map_url"],
            "additionalProperties": False,
        },
        "order": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["OUTRIGHT", "INSTALLMENT", "RENTAL", "MIXED"],
                },
                "code": {"type": ["string", "null"]},
                "delivery_date": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
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
                            "monthly_amount": {"type": ["number", "null"]},
                        },
                        "required": [
                            "name",
                            "qty",
                            "unit_price",
                            "line_total",
                            "item_type",
                            "monthly_amount",
                        ],
                        "additionalProperties": False,
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
                    "required": [
                        "delivery_fee",
                        "return_delivery_fee",
                        "penalty_fee",
                        "discount",
                    ],
                    "additionalProperties": False,
                },
                "plan": {
                    "type": "object",
                    "properties": {
                        "plan_type": {"type": ["string", "null"]},
                        "months": {"type": ["integer", "null"]},
                        "monthly_amount": {"type": ["number", "null"]},
                    },
                    "required": ["plan_type", "months", "monthly_amount"],
                    "additionalProperties": False,
                },
                "totals": {
                    "type": "object",
                    "properties": {
                        "subtotal": {"type": "number"},
                        "total": {"type": "number"},
                        "paid": {"type": "number"},
                        "to_collect": {"type": "number"},
                    },
                    "required": ["subtotal", "total", "paid", "to_collect"],
                    "additionalProperties": False,
                },
            },
            "required": [
                "type",
                "code",
                "delivery_date",
                "notes",
                "items",
                "charges",
                "plan",
                "totals",
            ],
            "additionalProperties": False,
        },
    },
    "required": ["customer", "order"],
    "additionalProperties": False,
}


SYSTEM = """You are a robust parser that outputs ONLY JSON that strictly conforms to the provided JSON Schema.

Task: Interpret Malaysian order messages for medical equipment sales/rentals and produce a normalized JSON object.

STRICT rules:
1) Items vs Charges
   - Emit a line as an item ONLY if it’s a product/service to be sold or rented.
   - DO NOT emit delivery/installation/pickup/return lines as items.
   - Map these to charges:
     • Delivery/penghantaran/pasang/installation: charges.delivery_fee
     • Return pickup/collect/ambil balik/ambil semula: charges.return_delivery_fee
     • Penalty/denda/cancellation fee: charges.penalty_fee
     • Discount/diskaun/less/"-RM10"/"RM10 off": charges.discount (positive number)
   - If the text says delivery is free/FOC/waived (“FOC”, “free”, “percuma”, “waive”), set delivery_fee = 0.

2) Item typing
   - OUTRIGHT when it’s a one-time purchase price (RM2200).
   - INSTALLMENT when pattern like “RM259 x 6 bulan / installment”, populate plan.months, items[i].monthly_amount.
   - RENTAL when “sewa”/“rent”, items[i].monthly_amount is the monthly rent.
   - If multiple types exist across items, order.type = "MIXED". Otherwise set to the sole type.

3) Totals semantics (populate if present, or set 0 when unknown; DO NOT fabricate):
   - totals.subtotal = SUM of item line totals (exclude all charges).
   - totals.total = subtotal - charges.discount + charges.delivery_fee + charges.return_delivery_fee + charges.penalty_fee.
   - totals.paid = amount already paid (0 if unknown).
   - totals.to_collect = total - paid (not negative).

4) Money formatting
   - Monetary values are numeric (no currency symbols), rounded to 2 decimals.
   - Quantities are numeric. If qty is missing, default to 1.

5) Delivery date & code
   - If a token like “WC2009” appears, set order.code to it.
   - delivery_date may be “19/8”, “19-08”, or embedded text like “Deliver 28/8”. Keep as provided string.

6) Safety
   - If you are not confident about a numeric, set it to 0 instead of guessing.
   - Do not invent items or fees not implied by the text.

Return only JSON that conforms to the provided schema. No extra keys. No comments."""


def parse_whatsapp_text(text: str) -> Dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = _openai_client()
    resp = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
        text={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "order",
                    "schema": SCHEMA,
                    "strict": True,
                },
            }
        },
    )
    parsed = resp.output_parsed
    if isinstance(parsed, dict):
        return parsed

    raw = resp.output_text
    if not raw and isinstance(parsed, str):
        raw = parsed
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}

