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
