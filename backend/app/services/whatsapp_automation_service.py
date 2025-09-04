"""WhatsApp Message Automation - From message to assigned order in seconds"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re
import phonenumbers
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.customer import Customer
from app.services.unified_assignment_service import UnifiedAssignmentService

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - WhatsApp automation disabled")


class WhatsAppAutomationService:
    """Fully automated WhatsApp to Order pipeline"""
    
    def __init__(self, db: Session, openai_api_key: Optional[str] = None):
        self.db = db
        self.openai_client = OpenAI(api_key=openai_api_key) if (openai_api_key and OPENAI_AVAILABLE) else None
        self.assignment_service = UnifiedAssignmentService(db, openai_api_key)

    def process_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main pipeline: WhatsApp message -> Order -> Assignment"""
        try:
            # Extract message details
            message_text = message_data.get("text", "")
            sender_phone = message_data.get("from", "")
            sender_name = message_data.get("sender_name", "")
            
            logger.info(f"Processing WhatsApp message from {sender_phone}: {message_text[:100]}...")
            
            # Pass 1: Intent Classification (fastest)
            intent_result = self._classify_intent(message_text)
            intent = intent_result.get("intent", "OTHER")
            confidence = intent_result.get("confidence", 0.0)
            
            if intent == "OTHER" or confidence < 0.7:
                return {
                    "success": False,
                    "message": "Not an order-related message",
                    "intent": intent,
                    "confidence": confidence,
                    "action": "ignored"
                }
            
            # Pass 2 or 3: Detailed parsing based on intent
            if intent == "DELIVERY":
                return self._handle_delivery_order(message_text, sender_phone, sender_name)
            elif intent == "PICKUP":
                return self._handle_pickup_request(message_text, sender_phone, sender_name)
                
        except Exception as e:
            logger.error(f"WhatsApp automation failed: {e}")
            return {
                "success": False,
                "message": f"Automation failed: {str(e)}",
                "error": str(e)
            }

    def _classify_intent(self, message: str) -> Dict[str, Any]:
        """Pass 1: Lightning-fast intent classification"""
        if not self.openai_client:
            # Fallback to keyword matching
            delivery_keywords = ["deliver", "send", "order", "buy", "purchase", "want", "need"]
            pickup_keywords = ["return", "cancel", "collect", "pickup", "refund", "installment"]
            
            message_lower = message.lower()
            delivery_score = sum(1 for word in delivery_keywords if word in message_lower)
            pickup_score = sum(1 for word in pickup_keywords if word in message_lower)
            
            if delivery_score > pickup_score:
                return {"intent": "DELIVERY", "confidence": 0.8}
            elif pickup_score > 0:
                return {"intent": "PICKUP", "confidence": 0.8}
            else:
                return {"intent": "OTHER", "confidence": 0.5}

        try:
            prompt = f"""
Classify this WhatsApp message quickly:

DELIVERY: New order, want to buy something, delivery request
PICKUP: Return, cancel, collect installment, refund request  
OTHER: Not order-related (greetings, questions, etc.)

Message: "{message}"

Respond with valid JSON only:
{{"intent": "DELIVERY|PICKUP|OTHER", "confidence": 0.95}}
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Fastest model
                messages=[
                    {"role": "system", "content": "You are a fast message classifier. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {"intent": "OTHER", "confidence": 0.0}

    def _handle_delivery_order(self, message: str, phone: str, name: str) -> Dict[str, Any]:
        """Pass 2: Parse delivery order and create + assign automatically"""
        try:
            # Parse order details with AI
            order_details = self._parse_delivery_details(message, phone, name)
            
            if not order_details.get("valid"):
                return {
                    "success": False,
                    "message": "Could not parse order details",
                    "details": order_details
                }
            
            # Create customer if not exists
            customer = self._get_or_create_customer(phone, name, order_details.get("address"))
            
            # Create order
            order = Order(
                customer_id=customer.id,
                code=self._generate_order_code(),
                status="PENDING",
                type="OUTRIGHT",  # Default, could be parsed from message
                total=order_details.get("total", 0),
                notes=f"Auto-created from WhatsApp: {order_details.get('notes', '')}",
                delivery_date=datetime.now().date()
            )
            
            self.db.add(order)
            self.db.flush()  # Get the order ID
            
            # Auto-assign immediately using unified service
            assignment_result = self.assignment_service.auto_assign_all()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Order #{order.code} created and auto-assigned!",
                "order_id": order.id,
                "order_code": order.code,
                "customer": customer.name,
                "assignment": assignment_result,
                "action": "created_and_assigned"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Delivery order creation failed: {e}")
            return {
                "success": False,
                "message": f"Failed to create order: {str(e)}",
                "error": str(e)
            }

    def _handle_pickup_request(self, message: str, phone: str, name: str) -> Dict[str, Any]:
        """Pass 3: Parse pickup/return request and create adjustment"""
        try:
            # Parse pickup details
            pickup_details = self._parse_pickup_details(message, phone, name)
            
            if not pickup_details.get("valid"):
                return {
                    "success": False,
                    "message": "Could not parse pickup details",
                    "details": pickup_details
                }
            
            # Find original order (if reference provided)
            original_order = None
            if pickup_details.get("order_reference"):
                original_order = self._find_original_order(
                    pickup_details["order_reference"], 
                    phone
                )
            
            # Create pickup order
            customer = self._get_or_create_customer(phone, name)
            pickup_order = Order(
                customer_id=customer.id,
                code=self._generate_order_code("PKP"),
                status="PENDING",
                type="PICKUP",
                notes=f"Auto-created pickup from WhatsApp: {pickup_details.get('reason', '')}",
                delivery_date=datetime.now().date()
            )
            
            self.db.add(pickup_order)
            self.db.flush()
            
            # Auto-assign pickup
            assignment_result = self.assignment_service.auto_assign_all()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Pickup #{pickup_order.code} created and assigned!",
                "pickup_id": pickup_order.id,
                "pickup_code": pickup_order.code,
                "original_order": original_order.code if original_order else None,
                "assignment": assignment_result,
                "action": "pickup_scheduled"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Pickup request failed: {e}")
            return {
                "success": False,
                "message": f"Failed to create pickup: {str(e)}",
                "error": str(e)
            }

    def _parse_delivery_details(self, message: str, phone: str, name: str) -> Dict[str, Any]:
        """Pass 2: Extract delivery order details with AI"""
        if not self.openai_client:
            return {"valid": False, "message": "AI not available for parsing"}
        
        try:
            prompt = f"""
Extract delivery order details from this WhatsApp message from {name} ({phone}):

Message: "{message}"

Extract:
1. Customer info (use provided name/phone if not in message)
2. Delivery address (full address)
3. Items and quantities 
4. Total amount (if mentioned)
5. Special delivery instructions

Respond with valid JSON:
{{
    "valid": true,
    "customer_name": "extracted or {name}",
    "phone": "{phone}",
    "address": "full delivery address",
    "items": [
        {{"name": "item name", "quantity": 1, "price": 100}}
    ],
    "total": 100.00,
    "notes": "special instructions",
    "delivery_date": "today|tomorrow|YYYY-MM-DD"
}}

If you cannot extract clear order details, return {{"valid": false, "reason": "explanation"}}
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting order details from casual WhatsApp messages. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Delivery parsing failed: {e}")
            return {"valid": False, "reason": f"Parsing error: {str(e)}"}

    def _parse_pickup_details(self, message: str, phone: str, name: str) -> Dict[str, Any]:
        """Pass 3: Extract pickup/return details with AI"""
        if not self.openai_client:
            return {"valid": False, "message": "AI not available for parsing"}
        
        try:
            prompt = f"""
Extract pickup/return details from this WhatsApp message from {name} ({phone}):

Message: "{message}"

Extract:
1. Reason (return, cancel, collect installment, etc.)
2. Original order reference (order number, receipt, etc.)
3. Items to collect (if specific)
4. Customer location for pickup
5. Urgency/timing

Respond with valid JSON:
{{
    "valid": true,
    "reason": "return|cancel|installment|refund",
    "order_reference": "order code or null",
    "items": ["item1", "item2"] or "all",
    "pickup_address": "address for collection",
    "notes": "additional details",
    "urgency": "today|tomorrow|normal"
}}

If not a clear pickup request, return {{"valid": false, "reason": "explanation"}}
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting pickup/return details from WhatsApp messages. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Pickup parsing failed: {e}")
            return {"valid": False, "reason": f"Parsing error: {str(e)}"}

    def _get_or_create_customer(self, phone: str, name: str, address: str = None) -> Customer:
        """Get existing customer or create new one"""
        # Normalize phone number
        normalized_phone = self._normalize_phone(phone)
        
        # Try to find existing customer
        customer = self.db.query(Customer).filter_by(phone=normalized_phone).first()
        
        if customer:
            # Update name if provided and current is empty
            if name and not customer.name:
                customer.name = name
            if address and not customer.address:
                customer.address = address
        else:
            # Create new customer
            customer = Customer(
                name=name or f"WhatsApp Customer {normalized_phone}",
                phone=normalized_phone,
                address=address,
                notes="Auto-created from WhatsApp"
            )
            self.db.add(customer)
            
        return customer

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to Malaysian format"""
        try:
            # Remove WhatsApp prefix and normalize
            clean_phone = re.sub(r'[^\d+]', '', phone)
            parsed = phonenumbers.parse(clean_phone, "MY")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            return phone  # Return original if parsing fails

    def _generate_order_code(self, prefix: str = "WA") -> str:
        """Generate unique order code"""
        timestamp = datetime.now().strftime("%m%d%H%M")
        return f"{prefix}{timestamp}"

    def _find_original_order(self, reference: str, customer_phone: str) -> Optional[Order]:
        """Find original order by reference and customer phone"""
        try:
            # Try exact code match first
            order = self.db.query(Order).filter_by(code=reference).first()
            if order and order.customer.phone == self._normalize_phone(customer_phone):
                return order
                
            # Try partial matches, recent orders from this customer
            customer = self.db.query(Customer).filter_by(
                phone=self._normalize_phone(customer_phone)
            ).first()
            
            if customer:
                # Get recent orders and try to match by code similarity
                recent_orders = (
                    self.db.query(Order)
                    .filter_by(customer_id=customer.id)
                    .order_by(Order.created_at.desc())
                    .limit(10)
                    .all()
                )
                
                for order in recent_orders:
                    if reference.lower() in order.code.lower():
                        return order
                        
            return None
            
        except Exception as e:
            logger.error(f"Error finding original order: {e}")
            return None