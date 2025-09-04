from __future__ import annotations

from typing import Any, Dict
from sqlalchemy.orm import Session

from .multi_stage_parser import multi_stage_parser
from .parser import parse_whatsapp_text  # Stage 2: Existing delivery parser
from .ordersvc import create_from_parsed
from .status_updates import apply_buyback, cancel_installment, mark_returned
from ..models import Order


class OrderNotFoundError(Exception):
    """Raised when mother order cannot be found for return/adjustment"""
    pass


class AmbiguousOrderError(Exception):
    """Raised when multiple possible mother orders found"""
    pass


class AdvancedParserService:
    """
    4-Stage LLM parsing pipeline for complex WhatsApp messages
    
    Stage 1: Message Classification (DELIVERY vs RETURN)
    Stage 2: Delivery Order Parsing (existing parser)
    Stage 3: Mother Order Finding (search & match)  
    Stage 4: Return/Adjustment Parsing (buyback, cancel, etc.)
    """
    
    def parse_whatsapp_message(self, db: Session, text: str) -> Dict[str, Any]:
        """Main entry point for advanced parsing"""
        
        # Stage 1: Classify message type
        classification = multi_stage_parser.classify_message(text)
        
        if classification["confidence"] < 0.5:
            return {
                "status": "unclear",
                "message": "Message unclear - please provide more specific information",
                "classification": classification
            }
        
        message_type = classification["message_type"]
        
        if message_type == "DELIVERY":
            return self._handle_delivery_message(db, text, classification)
        elif message_type == "RETURN":
            return self._handle_return_message(db, text, classification)
        else:
            return {
                "status": "unclear", 
                "message": "Could not determine if this is a delivery or return message",
                "classification": classification
            }

    def _handle_delivery_message(self, db: Session, text: str, classification: Dict) -> Dict[str, Any]:
        """Handle new order delivery messages"""
        try:
            # Stage 2: Use existing delivery parser
            order_data = parse_whatsapp_text(text)
            order = create_from_parsed(db, order_data)
            
            return {
                "status": "success",
                "type": "delivery",
                "order_id": order.id,
                "order_code": order.code,
                "message": f"New order {order.code} created successfully",
                "classification": classification,
                "parsed_data": order_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "type": "delivery", 
                "message": f"Failed to parse delivery order: {str(e)}",
                "classification": classification
            }

    def _handle_return_message(self, db: Session, text: str, classification: Dict) -> Dict[str, Any]:
        """Handle return/adjustment messages"""
        try:
            # Stage 3: Find mother order
            identifiers = multi_stage_parser.find_mother_order_identifiers(text)
            mother_order = multi_stage_parser.search_mother_order(db, identifiers)
            
            if not mother_order:
                return {
                    "status": "order_not_found",
                    "type": "return",
                    "message": "Cannot find original order. Please provide order code or customer name.",
                    "classification": classification,
                    "identifiers": identifiers
                }
            
            # Stage 4: Parse adjustment details
            adjustment_data = multi_stage_parser.parse_return_adjustment(text)
            
            # Apply the adjustment
            result_order = self._apply_adjustment(db, mother_order, adjustment_data)
            
            return {
                "status": "success",
                "type": "return",
                "mother_order_id": mother_order.id,
                "mother_order_code": mother_order.code,
                "adjustment_type": adjustment_data["adjustment_type"],
                "message": f"Applied {adjustment_data['adjustment_type'].lower()} to order {mother_order.code}",
                "classification": classification,
                "identifiers": identifiers,
                "adjustment_data": adjustment_data
            }
            
        except OrderNotFoundError as e:
            return {
                "status": "order_not_found",
                "type": "return",
                "message": str(e),
                "classification": classification
            }
        except Exception as e:
            return {
                "status": "error",
                "type": "return",
                "message": f"Failed to process return: {str(e)}",
                "classification": classification
            }

    def _apply_adjustment(self, db: Session, mother_order: Order, adjustment_data: Dict[str, Any]) -> Order:
        """Apply the appropriate adjustment to the mother order"""
        
        adjustment_type = adjustment_data["adjustment_type"]
        
        if adjustment_type == "BUYBACK":
            if not adjustment_data.get("amount"):
                raise ValueError("Buyback amount is required")
                
            return apply_buyback(
                db=db,
                order=mother_order,
                amount=adjustment_data["amount"],
                discount=adjustment_data.get("discount"),
                method=adjustment_data.get("method"),
                reference=adjustment_data.get("reference")
            )
            
        elif adjustment_type == "INSTALLMENT_CANCEL":
            return cancel_installment(
                db=db,
                order=mother_order,
                penalty=adjustment_data.get("penalty", 0),
                return_delivery_fee=adjustment_data.get("return_delivery_fee", 0),
                collect=adjustment_data.get("collect", False),
                method=adjustment_data.get("method"),
                reference=adjustment_data.get("reference")
            )
            
        elif adjustment_type == "RENTAL_RETURN":
            return mark_returned(
                db=db,
                order=mother_order,
                return_delivery_fee=adjustment_data.get("return_delivery_fee", 0),
                collect=adjustment_data.get("collect", False)
            )
            
        elif adjustment_type == "GENERAL_CANCEL":
            # Simple cancellation - set status and optionally add penalty
            mother_order.status = "CANCELLED"
            if adjustment_data.get("penalty", 0) > 0:
                mother_order.penalty_fee = adjustment_data["penalty"]
            db.add(mother_order)
            db.commit()
            return mother_order
            
        else:
            raise ValueError(f"Unknown adjustment type: {adjustment_type}")


# Global instance
advanced_parser = AdvancedParserService()