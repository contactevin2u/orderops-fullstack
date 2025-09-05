from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Role
from ..auth.deps import require_roles
from ..services.advanced_parser import advanced_parser
from ..utils.responses import envelope

router = APIRouter(
    prefix="/parse",
    tags=["parse"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)


    
class AdvancedParseIn(BaseModel):
    text: str = ""
    message: str = ""  # alias for text to support both formats
    
    def get_message_text(self) -> str:
        """Get the message text from either field"""
        return (self.text or self.message or "").strip()


@router.post("/advanced", response_model=dict)
def parse_advanced_message(body: AdvancedParseIn, db: Session = Depends(get_session)):
    """
    Advanced 4-stage LLM parsing pipeline for complex WhatsApp messages.
    
    Handles both delivery orders and returns/adjustments (buybacks, cancellations, etc.)
    """
    raw = body.get_message_text()
    if not raw:
        raise HTTPException(400, "text or message is required")

    try:
        result = advanced_parser.parse_whatsapp_message(db, raw)
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(500, f"Advanced parsing failed: {str(e)}")


@router.post("/classify", response_model=dict)  
def classify_message(body: AdvancedParseIn):
    """
    Stage 1 only: Classify message as DELIVERY or RETURN
    """
    raw = body.get_message_text()
    if not raw:
        raise HTTPException(400, "text or message is required")
        
    try:
        from ..services.multi_stage_parser import multi_stage_parser
        result = multi_stage_parser.classify_message(raw)
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(500, f"Classification failed: {str(e)}")


@router.post("/find-order", response_model=dict)
def find_mother_order(body: AdvancedParseIn, db: Session = Depends(get_session)):
    """
    Stage 3 only: Find mother order for return/adjustment messages
    """
    raw = body.get_message_text()
    if not raw:
        raise HTTPException(400, "text or message is required")
        
    try:
        from ..services.multi_stage_parser import multi_stage_parser
        identifiers = multi_stage_parser.find_mother_order_identifiers(raw)
        mother_order = multi_stage_parser.search_mother_order(db, identifiers)
        
        result = {
            "identifiers": identifiers,
            "mother_order": None
        }
        
        if mother_order:
            result["mother_order"] = {
                "id": mother_order.id,
                "code": mother_order.code,
                "customer_name": mother_order.customer.name if mother_order.customer else None,
                "type": mother_order.type,
                "status": mother_order.status,
                "total": float(mother_order.total or 0)
            }
            
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(500, f"Order search failed: {str(e)}")


@router.post("/quotation", response_model=dict)
def parse_quotation_message(body: AdvancedParseIn):
    """
    Simple parser for quotation messages - returns structured data without creating orders
    """
    raw = body.get_message_text()
    if not raw:
        raise HTTPException(400, "text or message is required")
        
    try:
        result = _simple_quotation_parser(raw)
        return envelope({"parsed": result})
        
    except Exception as e:
        raise HTTPException(500, f"Quotation parsing failed: {str(e)}")


def _simple_quotation_parser(text: str) -> dict:
    """
    OpenAI-powered parser for quotation messages
    Returns structured data matching the quotation form fields
    """
    from ..core.config import settings
    import json
    
    # Try OpenAI first if available
    if settings.OPENAI_API_KEY:
        try:
            return _openai_quotation_parser(text)
        except Exception as e:
            # Fall back to regex parser if OpenAI fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"OpenAI quotation parser failed, falling back to regex: {e}")
    
    # Fallback regex parser
    return _regex_quotation_parser(text)


def _openai_quotation_parser(text: str) -> dict:
    """OpenAI-powered quotation parser"""
    from ..core.config import settings
    from openai import OpenAI
    import json
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    schema = {
        "type": "object",
        "properties": {
            "customer": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"}
                },
                "required": ["name", "phone", "address"],
                "additionalProperties": False
            },
            "order": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["OUTRIGHT", "INSTALLMENT", "RENTAL", "MIXED"]
                    },
                    "delivery_date": {"type": "string"},
                    "notes": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "item_type": {
                                    "type": "string",
                                    "enum": ["OUTRIGHT", "INSTALLMENT", "RENTAL", "FEE"]
                                },
                                "qty": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "line_total": {"type": "number"},
                                "monthly_amount": {"type": "number"}
                            },
                            "required": ["name", "item_type", "qty", "unit_price", "line_total"],
                            "additionalProperties": False
                        }
                    },
                    "charges": {
                        "type": "object",
                        "properties": {
                            "delivery_fee": {"type": "number"},
                            "return_delivery_fee": {"type": "number"}
                        },
                        "required": ["delivery_fee", "return_delivery_fee"],
                        "additionalProperties": False
                    },
                    "plan": {
                        "type": "object",
                        "properties": {
                            "plan_type": {"type": "string"},
                            "months": {"type": "number"},
                            "monthly_amount": {"type": "number"}
                        },
                        "required": ["plan_type", "months", "monthly_amount"],
                        "additionalProperties": False
                    }
                },
                "required": ["type", "delivery_date", "notes", "items", "charges", "plan"],
                "additionalProperties": False
            }
        },
        "required": ["customer", "order"],
        "additionalProperties": False
    }
    
    system_prompt = """You are a quotation parser for an appliance rental/sales business in Malaysia. 
Parse the following message and extract customer information and order details.

Rules:
- Extract customer name, phone, and address
- Determine order type: OUTRIGHT (purchase), INSTALLMENT (hire purchase), RENTAL (rent), or MIXED
- Parse items with quantities and prices (in RM Malaysian Ringgit)
- Calculate line_total as qty * unit_price for each item
- Extract delivery fees and return delivery fees
- For installment/rental plans, extract plan details
- Convert dates to YYYY-MM-DD format
- Use empty strings for missing text fields, 0 for missing numbers
- Item types: OUTRIGHT, INSTALLMENT, RENTAL, or FEE (for delivery charges)
- If delivery fee is mentioned as a separate line item, include it in items array with item_type "FEE"

Return structured JSON matching the exact schema provided."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "quotation", "schema": schema, "strict": True}
        },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    
    content = response.choices[0].message.content
    if isinstance(content, str):
        return json.loads(content)
    return content


def _regex_quotation_parser(text: str) -> dict:
    """
    Fallback regex-based parser for quotation messages
    Returns structured data matching the quotation form fields
    """
    import re
    from decimal import Decimal
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    result = {
        "customer": {
            "name": "",
            "phone": "",
            "address": ""
        },
        "order": {
            "type": "OUTRIGHT",
            "delivery_date": "",
            "notes": "",
            "items": [],
            "charges": {
                "delivery_fee": 0,
                "return_delivery_fee": 0
            },
            "plan": {
                "plan_type": "",
                "months": 0,
                "monthly_amount": 0
            }
        }
    }
    
    current_section = None
    
    for line in lines:
        line_lower = line.lower()
        
        # Customer info
        if 'customer' in line_lower or 'name' in line_lower:
            if ':' in line:
                result["customer"]["name"] = line.split(':', 1)[1].strip()
        elif 'phone' in line_lower:
            if ':' in line:
                result["customer"]["phone"] = line.split(':', 1)[1].strip()
        elif 'address' in line_lower:
            if ':' in line:
                result["customer"]["address"] = line.split(':', 1)[1].strip()
        
        # Order type
        elif any(t in line_lower for t in ['outright', 'installment', 'rental', 'mixed']):
            for order_type in ['OUTRIGHT', 'INSTALLMENT', 'RENTAL', 'MIXED']:
                if order_type.lower() in line_lower:
                    result["order"]["type"] = order_type
                    break
        
        # Items section
        elif 'item' in line_lower and ':' not in line:
            current_section = 'items'
        elif current_section == 'items' or line.startswith('-') or line.startswith('•'):
            item_match = re.search(r'(.+?)\s*(?:\(([A-Z]+)\))?\s*-?\s*(\d+)\s*x?\s*(?:rm|RM)?\s*(\d+(?:\.\d{2})?)', line, re.IGNORECASE)
            if item_match:
                name = item_match.group(1).strip()
                item_type = item_match.group(2) or 'OUTRIGHT'
                qty = int(item_match.group(3))
                price = float(item_match.group(4))
                
                result["order"]["items"].append({
                    "name": name,
                    "item_type": item_type,
                    "qty": qty,
                    "unit_price": price,
                    "line_total": qty * price,
                    "monthly_amount": 0
                })
        
        # Fees
        elif 'delivery' in line_lower and 'fee' in line_lower:
            fee_match = re.search(r'(?:rm|RM)?\s*(\d+(?:\.\d{2})?)', line)
            if fee_match:
                fee = float(fee_match.group(1))
                if 'return' in line_lower:
                    result["order"]["charges"]["return_delivery_fee"] = fee
                else:
                    result["order"]["charges"]["delivery_fee"] = fee
        
        # Plan info
        elif any(p in line_lower for p in ['installment', 'rental']) and 'month' in line_lower:
            months_match = re.search(r'(\d+)\s*month', line, re.IGNORECASE)
            amount_match = re.search(r'(?:rm|RM)?\s*(\d+(?:\.\d{2})?)', line)
            
            if months_match:
                result["order"]["plan"]["months"] = int(months_match.group(1))
            if amount_match:
                result["order"]["plan"]["monthly_amount"] = float(amount_match.group(1))
            
            if 'installment' in line_lower:
                result["order"]["plan"]["plan_type"] = "INSTALLMENT"
            elif 'rental' in line_lower:
                result["order"]["plan"]["plan_type"] = "RENTAL"
        
        # Notes
        elif 'note' in line_lower or 'remark' in line_lower:
            if ':' in line:
                result["order"]["notes"] = line.split(':', 1)[1].strip()
        
        # Date
        elif 'date' in line_lower or 'deliver' in line_lower:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', line)
            if date_match:
                date_str = date_match.group(1)
                # Convert to YYYY-MM-DD format
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts[2]) == 4:  # DD/MM/YYYY
                        result["order"]["delivery_date"] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                elif '-' in date_str and len(date_str.split('-')[0]) == 2:  # DD-MM-YYYY
                    parts = date_str.split('-')
                    result["order"]["delivery_date"] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                else:  # Already YYYY-MM-DD
                    result["order"]["delivery_date"] = date_str
    
    return result
