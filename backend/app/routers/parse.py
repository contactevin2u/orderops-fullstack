from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_session
from ..services.parser import parse_whatsapp_text
from ..services import parser as parser_service
from ..schemas import OrderCreateIn, OrderOut
from ..services.ordersvc import create_order_from_parsed

router = APIRouter(prefix="/parse", tags=["parse"])

class ParseIn(BaseModel):
    text: str
    create_order: bool = False

@router.post("", response_model=dict)
def parse_only(body: ParseIn, db: Session = Depends(get_session)):
    parsed = parse_whatsapp_text(body.text)
    if body.create_order:
        try:
            order = create_order_from_parsed(db, parsed)
            return {"parsed": parsed, "created_order_id": order.id, "order_code": order.code}
        except Exception as e:
            raise HTTPException(400, f"Create failed: {e}")
    return {"parsed": parsed}
