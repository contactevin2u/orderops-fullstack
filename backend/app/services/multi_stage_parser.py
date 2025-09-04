from __future__ import annotations

import json
from typing import Any, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.config import settings
from ..models import Order, Customer
from .parser import _openai_client


# Stage 1: Message Classification
CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "message_type": {
            "type": "string",
            "enum": ["DELIVERY", "RETURN", "UNCLEAR"]
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"}
    },
    "required": ["message_type", "confidence", "reasoning"],
    "additionalProperties": False
}

CLASSIFIER_PROMPT = """You are a message classifier for Malaysian medical equipment orders.

Classify messages as:
- DELIVERY: New orders, deliveries, installations
- RETURN: Buybacks, cancellations, returns, adjustments, refunds
- UNCLEAR: Cannot determine type

DELIVERY indicators:
- New customer details (name, phone, address)
- Equipment lists with quantities and prices
- "hantar", "deliver", "pasang", "install", "sewa", "rent", "beli", "buy"
- Complete order information
- Fresh order codes with full details

RETURN indicators:  
- "buyback", "beli balik", "refund"
- "cancel", "batal", "pembatalan"
- "return", "ambil balik", "ambil semula"
- "denda", "penalty", "fine"
- Order codes mentioned alone without full order details
- Adjustment amounts mentioned

Examples:
✓ DELIVERY: "WC2024 hantar kepada Ahmad 012-3456789 wheelchair RM2000 sewa 6 bulan"
✓ RETURN: "WC2024 buyback RM500"
✓ RETURN: "Cancel WC2024 dengan denda RM100"
✓ RETURN: "Ambil balik order Ahmad wheelchair"
✗ UNCLEAR: "Hello, how are you?"

Return ONLY JSON matching the schema."""

# Stage 3: Mother Order Finder
MOTHER_FINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "order_codes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "customer_identifiers": {
            "type": "array",
            "items": {"type": "string"}
        },
        "equipment_keywords": {
            "type": "array", 
            "items": {"type": "string"}
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["order_codes", "customer_identifiers", "equipment_keywords", "confidence"],
    "additionalProperties": False
}

MOTHER_FINDER_PROMPT = """Extract identifiers to find the original order from return/adjustment messages.

Look for:
1. Order codes: "WC2024", "KP1234", alphanumeric patterns (2-4 letters + numbers)
2. Customer names: Proper names (Ahmad, Siti, Dr. Lim, etc.)
3. Equipment keywords: "wheelchair", "kerusi roda", "hospital bed", "katil", "oxygen", specific equipment mentioned
4. Location hints: "Ampang", "KL", "Selangor" (for address matching)

Examples:
"WC2024 buyback RM300 Ahmad" → {
  "order_codes": ["WC2024"], 
  "customer_identifiers": ["Ahmad"],
  "equipment_keywords": [],
  "confidence": 0.9
}

"Cancel wheelchair untuk Siti di Ampang" → {
  "order_codes": [],
  "customer_identifiers": ["Siti", "Ampang"], 
  "equipment_keywords": ["wheelchair"],
  "confidence": 0.7
}

"Ambil balik katil hospital Dr Wong" → {
  "order_codes": [],
  "customer_identifiers": ["Dr Wong"],
  "equipment_keywords": ["katil", "hospital"],
  "confidence": 0.8
}

Return ONLY JSON matching the schema."""

# Stage 4: Return/Adjustment Parser  
RETURN_PARSER_SCHEMA = {
    "type": "object",
    "properties": {
        "adjustment_type": {
            "type": "string",
            "enum": ["BUYBACK", "INSTALLMENT_CANCEL", "RENTAL_RETURN", "GENERAL_CANCEL"]
        },
        "amount": {"type": ["number", "null"]},
        "penalty": {"type": ["number", "null"]},
        "return_delivery_fee": {"type": ["number", "null"]},
        "discount": {
            "type": ["object", "null"],
            "properties": {
                "type": {"type": "string", "enum": ["percent", "fixed"]},
                "value": {"type": "number"}
            },
            "additionalProperties": False
        },
        "method": {"type": ["string", "null"]},
        "reference": {"type": ["string", "null"]},
        "collect": {"type": "boolean"},
        "date": {"type": ["string", "null"]},
        "notes": {"type": ["string", "null"]}
    },
    "required": ["adjustment_type", "collect"],
    "additionalProperties": False
}

RETURN_PARSER_PROMPT = """Parse Malaysian return/adjustment messages into structured adjustment data.

Adjustment types:
- BUYBACK: "buyback", "beli balik" - company buys back equipment
- INSTALLMENT_CANCEL: "cancel installment", "batal ansuran" - cancel installment plan
- RENTAL_RETURN: "return rental", "tamat sewa", "ambil balik sewa" - end rental 
- GENERAL_CANCEL: "cancel", "batal" - general cancellation

Extract:
- amount: RM values mentioned
- penalty: "denda", "penalty", "fine" amounts
- return_delivery_fee: "pickup fee", "collection fee"
- discount: "diskaun", "less", "potongan" 
- collect: true if "collect", "pickup", "ambil"; false if "no collect", "customer return"
- method: "cash", "bank", "card"
- reference: transaction IDs, receipt numbers
- date: if specific date mentioned
- notes: additional context

Examples:

"WC2024 buyback RM500 dengan diskaun 10%" → {
  "adjustment_type": "BUYBACK",
  "amount": 500,
  "discount": {"type": "percent", "value": 10},
  "collect": false
}

"Cancel installment dengan denda RM100, pickup fee RM20" → {
  "adjustment_type": "INSTALLMENT_CANCEL", 
  "penalty": 100,
  "return_delivery_fee": 20,
  "collect": true
}

"Tamat sewa wheelchair, customer hantar sendiri" → {
  "adjustment_type": "RENTAL_RETURN",
  "collect": false
}

Return ONLY JSON matching the schema."""


class MultiStageParser:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client = _openai_client()

    def classify_message(self, text: str) -> Dict[str, Any]:
        """Stage 1: Classify message as DELIVERY or RETURN"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "classification", "schema": CLASSIFIER_SCHEMA, "strict": True}
            },
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        
        msg = response.choices[0].message
        raw = getattr(msg, "content", None) or getattr(msg, "parsed", "{}")
        if isinstance(raw, dict):
            return raw
        return json.loads(raw or "{}")

    def find_mother_order_identifiers(self, text: str) -> Dict[str, Any]:
        """Stage 3: Extract identifiers to find original order"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={
                "type": "json_schema", 
                "json_schema": {"name": "identifiers", "schema": MOTHER_FINDER_SCHEMA, "strict": True}
            },
            messages=[
                {"role": "system", "content": MOTHER_FINDER_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        
        msg = response.choices[0].message
        raw = getattr(msg, "content", None) or getattr(msg, "parsed", "{}")
        if isinstance(raw, dict):
            return raw
        return json.loads(raw or "{}")

    def parse_return_adjustment(self, text: str) -> Dict[str, Any]:
        """Stage 4: Parse return/adjustment details"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "adjustment", "schema": RETURN_PARSER_SCHEMA, "strict": True}
            },
            messages=[
                {"role": "system", "content": RETURN_PARSER_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        
        msg = response.choices[0].message  
        raw = getattr(msg, "content", None) or getattr(msg, "parsed", "{}")
        if isinstance(raw, dict):
            return raw
        return json.loads(raw or "{}")

    def search_mother_order(self, db: Session, identifiers: Dict[str, Any]) -> Order | None:
        """Multi-strategy search for mother order"""
        
        # Strategy 1: Direct order code match (highest priority)
        for code in identifiers.get("order_codes", []):
            if code and len(code.strip()) >= 3:  # Valid order code
                order = db.query(Order).filter(Order.code.ilike(f"%{code.strip()}%")).first()
                if order:
                    return order

        # Strategy 2: Customer name match + recent orders  
        customer_names = [name.strip() for name in identifiers.get("customer_identifiers", []) if name and len(name.strip()) >= 2]
        
        if customer_names:
            # Build name matching conditions
            name_conditions = []
            for name in customer_names:
                name_conditions.append(Customer.name.ilike(f"%{name}%"))
            
            # Find orders from last 90 days with matching customer names
            recent_cutoff = datetime.now() - timedelta(days=90)
            orders = (db.query(Order)
                     .join(Customer)
                     .filter(or_(*name_conditions) if name_conditions else False)
                     .filter(Order.created_at > recent_cutoff)
                     .filter(Order.status.in_(["ACTIVE", "NEW", "DELIVERED"]))  # Only active orders
                     .order_by(Order.created_at.desc())
                     .limit(10)
                     .all())
            
            # If single match, return it
            if len(orders) == 1:
                return orders[0]
            
            # If multiple matches, try to narrow down by equipment keywords
            equipment_keywords = identifiers.get("equipment_keywords", [])
            if equipment_keywords and len(orders) > 1:
                for order in orders:
                    order_text = f"{order.notes or ''} {' '.join(item.name for item in order.items)}"
                    for keyword in equipment_keywords:
                        if keyword.lower() in order_text.lower():
                            return order
            
            # If still multiple matches, return most recent
            if orders:
                return orders[0]

        return None


# Global instance
multi_stage_parser = MultiStageParser()