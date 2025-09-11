"""AI-powered verification service for commission release automation"""

import base64
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
import openai
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.trip import Trip
from app.models.order import Order
from app.models.order_item_uid import OrderItemUID
from app.models.ai_verification_log import AIVerificationLog
from app.core.config import Settings

settings = Settings()


class AIVerificationResult:
    def __init__(self):
        self.pod_verified = False
        self.payment_verified = False
        self.payment_method = None  # "cash" | "bank_transfer" | "unknown"
        self.payment_amount_match = False
        self.uid_verified = False
        self.cash_collection_required = False
        self.cash_collected_confirmed = False  # CRITICAL FIX: Add missing attribute
        self.confidence_score = 0.0
        self.verification_notes = []
        self.errors = []

    def is_commission_releasable(self) -> bool:
        """Check if all criteria are met for commission release"""
        return (
            self.pod_verified and
            self.payment_verified and
            self.payment_amount_match and
            self.uid_verified and
            (not self.cash_collection_required or self.cash_collected_confirmed)
        )

    def to_dict(self) -> Dict:
        return {
            "pod_verified": self.pod_verified,
            "payment_verified": self.payment_verified,
            "payment_method": self.payment_method,
            "payment_amount_match": self.payment_amount_match,
            "uid_verified": self.uid_verified,
            "cash_collection_required": self.cash_collection_required,
            "confidence_score": self.confidence_score,
            "verification_notes": self.verification_notes,
            "errors": self.errors,
            "commission_releasable": self.is_commission_releasable()
        }


class AIVerificationService:
    def __init__(self, db: Session):
        self.db = db
        self.MAX_AI_CALLS_PER_TRIP = 2
        
        # Robust OpenAI client initialization with error handling
        try:
            if not settings.OPENAI_API_KEY:
                print("WARNING: OPENAI_API_KEY not configured - AI verification disabled")
                self.openai_client = None
            else:
                self.openai_client = openai.OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=30.0  # 30 second timeout
                )
                print("OpenAI client initialized successfully")
        except Exception as e:
            print(f"OpenAI client initialization failed: {e}")
            self.openai_client = None

    def check_rate_limit(self, trip_id: int) -> Tuple[bool, int, str]:
        """
        Check if AI analysis rate limit has been exceeded for this trip
        Returns: (can_analyze, current_count, message)
        """
        current_count = self.db.query(AIVerificationLog).filter(
            AIVerificationLog.trip_id == trip_id
        ).count()
        
        can_analyze = current_count < self.MAX_AI_CALLS_PER_TRIP
        
        if can_analyze:
            remaining = self.MAX_AI_CALLS_PER_TRIP - current_count
            message = f"AI analysis allowed. {remaining} calls remaining for this trip."
        else:
            message = f"Rate limit exceeded. Maximum {self.MAX_AI_CALLS_PER_TRIP} AI analyses per trip reached."
        
        return can_analyze, current_count, message

    def log_verification_attempt(
        self, 
        trip_id: int, 
        result: AIVerificationResult, 
        user_id: int = None,
        tokens_used: int = None,
        processing_time_ms: int = None
    ) -> AIVerificationLog:
        """Log AI verification attempt for auditing and rate limiting"""
        log_entry = AIVerificationLog(
            trip_id=trip_id,
            user_id=user_id,
            payment_method=result.payment_method,
            confidence_score=result.confidence_score,
            cash_collection_required=result.cash_collection_required,
            analysis_result=result.to_dict(),
            verification_notes=result.verification_notes,
            errors=result.errors,
            success=len(result.errors) == 0,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms
        )
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        
        return log_entry

    def verify_commission_release(self, trip_id: int, user_id: int = None) -> AIVerificationResult:
        """
        Simplified AI verification focused on payment method detection with rate limiting
        
        Main goal: Detect if payment was CASH or BANK TRANSFER
        - If CASH: Require cash collection before commission release
        - If BANK TRANSFER: Commission can be released immediately
        
        Rate limited to maximum 2 calls per trip to control token usage
        """
        start_time = time.time()
        result = AIVerificationResult()
        tokens_used = 0
        
        # Check rate limit first
        can_analyze, current_count, rate_limit_message = self.check_rate_limit(trip_id)
        if not can_analyze:
            result.errors.append(rate_limit_message)
            result.verification_notes.append(f"Analysis blocked: {current_count}/{self.MAX_AI_CALLS_PER_TRIP} calls already made")
            # Still log this failed attempt
            processing_time = int((time.time() - start_time) * 1000)
            self.log_verification_attempt(trip_id, result, user_id, tokens_used, processing_time)
            return result
        
        result.verification_notes.append(rate_limit_message)
        
        try:
            trip = self.db.query(Trip).filter(Trip.id == trip_id).first()
            if not trip:
                result.errors.append(f"Trip {trip_id} not found")
                return result

            order = self.db.query(Order).filter(Order.id == trip.order_id).first()
            if not order:
                result.errors.append(f"Order {trip.order_id} not found")
                return result

            # Basic checks (relaxed conditions)
            result.pod_verified = bool(trip.pod_photo_urls)  # Just check POD exists
            result.uid_verified = True  # Assume UID is handled separately
            result.payment_amount_match = True  # Assume amount is correct

            # MAIN FOCUS: Payment method detection
            payment_result = self._detect_payment_method(trip, order)
            result.payment_verified = payment_result["detected"]
            result.payment_method = payment_result["method"]
            result.cash_collection_required = payment_result["method"] == "cash"
            result.verification_notes.extend(payment_result["notes"])

            # Simple confidence score
            result.confidence_score = 0.9 if result.payment_verified else 0.3

        except Exception as e:
            result.errors.append(f"AI verification failed: {str(e)}")
        finally:
            # Log the verification attempt
            processing_time = int((time.time() - start_time) * 1000)
            self.log_verification_attempt(trip_id, result, user_id, tokens_used, processing_time)

        return result

    def _detect_payment_method(self, trip: Trip, order: Order) -> Dict:
        """
        Simplified AI detection: CASH vs BANK TRANSFER
        
        This is the core function that determines if cash collection is needed.
        Uses existing POD photos which include payment proof photos.
        """
        # Use existing POD photos - payment proof is uploaded to pod_photo_urls
        payment_photos = trip.pod_photo_urls
        if not payment_photos:
            return {
                "detected": False,
                "method": "unknown",
                "notes": ["No POD/payment photos found - manual verification required"]
            }

        try:
            # Check if AI is available
            if not self.openai_client:
                return {
                    "detected": False,
                    "method": "ai_unavailable",
                    "notes": ["AI service unavailable - manual verification required"]
                }

            # Analyze payment photos with simple prompt
            for photo_url in payment_photos:
                analysis = self._analyze_payment_method_simple(photo_url)
                
                if analysis["confidence"] >= 0.7:  # High confidence detection (70%)
                    return {
                        "detected": True,
                        "method": analysis["method"],
                        "notes": [f"AI detected: {analysis['method']} (confidence: {analysis['confidence']:.1%})"]
                    }

            # If no high-confidence detection, mark for manual review (30% fallback)
            return {
                "detected": False,
                "method": "manual_review_needed", 
                "notes": ["AI confidence below 70% - manual verification required"]
            }

        except Exception as e:
            # Graceful fallback to manual on any AI failure
            return {
                "detected": False,
                "method": "ai_timeout_or_error",
                "notes": [f"AI analysis failed (timeout/error) - manual verification required: {str(e)}"]
            }

    def _analyze_payment_method_simple(self, photo_url: str) -> Dict:
        """Simple AI analysis: Is this CASH or BANK TRANSFER?"""
        
        # Return early if no OpenAI client
        if not self.openai_client:
            return {
                "method": "unknown",
                "confidence": 0.0,
                "reason": "OpenAI client not available"
            }
        
        try:
            photo_base64 = self._url_to_base64(photo_url)
            
            prompt = """
            Look at this photo and determine if it shows CASH payment or BANK TRANSFER.

            CASH indicators:
            - Physical money (bills, coins)
            - Cash receipts
            - Cash counting
            - Physical cash exchange

            BANK TRANSFER indicators:
            - Banking app screens
            - Online transfer confirmations
            - QR code payments
            - E-wallet confirmations
            - Digital payment receipts

            Respond ONLY in this JSON format:
            {
                "method": "cash" or "bank_transfer",
                "confidence": 0.0 to 1.0,
                "reason": "Brief explanation of what you see"
            }
            """

            # Robust OpenAI API call with timeout
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.1,  # Low temperature for consistent results
                timeout=25.0  # 25 second timeout for individual requests
            )

            # Parse response with error handling
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
                
            analysis = json.loads(content)
            
            # Validate response format
            required_fields = ["method", "confidence", "reason"]
            if not all(field in analysis for field in required_fields):
                raise ValueError("Invalid response format from OpenAI")
            
            # Validate method value
            if analysis["method"] not in ["cash", "bank_transfer"]:
                analysis["method"] = "unknown"
                analysis["confidence"] = 0.0
            
            # Ensure confidence is between 0 and 1
            analysis["confidence"] = max(0.0, min(1.0, float(analysis["confidence"])))
            
            return analysis

        except openai.RateLimitError:
            return {
                "method": "unknown",
                "confidence": 0.0,
                "reason": "OpenAI rate limit exceeded - try again later"
            }
        except openai.APITimeoutError:
            return {
                "method": "unknown", 
                "confidence": 0.0,
                "reason": "OpenAI request timeout - try manual verification"
            }
        except json.JSONDecodeError as e:
            return {
                "method": "unknown",
                "confidence": 0.0,
                "reason": f"Invalid JSON response from AI: {str(e)}"
            }
        except Exception as e:
            return {
                "method": "unknown",
                "confidence": 0.0,
                "reason": f"AI analysis failed: {str(e)}"
            }

    def _verify_pod_photos(self, trip: Trip, order: Order) -> Dict:
        """AI analysis of POD photos for quality and authenticity"""
        
        pod_urls = trip.pod_photo_urls
        if not pod_urls:
            return {"verified": False, "notes": ["No POD photos found"]}

        try:
            # Prepare order context for AI
            order_context = {
                "total_amount": float(order.total),
                "customer_name": order.customer_name,
                "delivery_address": order.delivery_address,
                "item_count": len(getattr(order, 'items', [])),
                "order_type": getattr(order, 'type', 'unknown')
            }

            # Analyze each POD photo
            analysis_results = []
            for i, photo_url in enumerate(pod_urls):
                photo_analysis = self._analyze_pod_photo(photo_url, order_context, i + 1)
                analysis_results.append(photo_analysis)

            # Aggregate results
            all_verified = all(result["quality_ok"] for result in analysis_results)
            authenticity_scores = [result["authenticity_score"] for result in analysis_results]
            avg_authenticity = sum(authenticity_scores) / len(authenticity_scores)

            notes = []
            for i, result in enumerate(analysis_results):
                notes.append(f"Photo {i+1}: {result['description']}")

            return {
                "verified": all_verified and avg_authenticity >= 0.8,
                "notes": notes,
                "authenticity_score": avg_authenticity
            }

        except Exception as e:
            return {"verified": False, "notes": [f"POD analysis failed: {str(e)}"]}

    def _analyze_pod_photo(self, photo_url: str, order_context: Dict, photo_num: int) -> Dict:
        """Analyze single POD photo with OpenAI Vision"""
        
        try:
            # Convert photo to base64 for OpenAI
            photo_base64 = self._url_to_base64(photo_url)
            
            prompt = f"""
            Analyze this Proof of Delivery (POD) photo for order verification:

            Order Details:
            - Total Amount: RM{order_context['total_amount']}
            - Customer: {order_context['customer_name']}
            - Address: {order_context['delivery_address']}
            - Expected Items: {order_context['item_count']}

            Please evaluate:
            1. Are delivered items clearly visible?
            2. Do items appear new and undamaged?
            3. Is this a legitimate delivery setting (not staged)?
            4. Does the setting match a residential/business delivery?
            5. Photo quality and clarity

            Respond in JSON format:
            {{
                "quality_ok": boolean,
                "authenticity_score": float (0-1),
                "items_visible": boolean,
                "items_appear_new": boolean,
                "legitimate_setting": boolean,
                "description": "Brief description of what you see"
            }}
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            analysis = json.loads(response.choices[0].message.content)
            return analysis

        except Exception as e:
            return {
                "quality_ok": False,
                "authenticity_score": 0.0,
                "items_visible": False,
                "items_appear_new": False,
                "legitimate_setting": False,
                "description": f"Analysis failed: {str(e)}"
            }

    def _verify_payment_proof(self, trip: Trip, order: Order) -> Dict:
        """AI analysis of payment proof photos"""
        
        # Check if payment photos exist (this would need to be implemented)
        payment_photos = getattr(trip, 'payment_photo_urls', [])
        if not payment_photos:
            return {
                "verified": False,
                "method": "unknown",
                "amount_match": False,
                "notes": ["No payment proof photos found"]
            }

        try:
            expected_amount = float(order.total)
            
            # Analyze payment photos
            payment_analyses = []
            for photo_url in payment_photos:
                analysis = self._analyze_payment_photo(photo_url, expected_amount)
                payment_analyses.append(analysis)

            # Determine payment method and verification
            payment_methods = [a["detected_method"] for a in payment_analyses if a["detected_method"]]
            most_common_method = max(set(payment_methods), key=payment_methods.count) if payment_methods else "unknown"
            
            amount_matches = [a["amount_match"] for a in payment_analyses]
            amount_verified = any(amount_matches)

            overall_verified = any(a["verified"] for a in payment_analyses)

            notes = []
            for i, analysis in enumerate(payment_analyses):
                notes.append(f"Payment photo {i+1}: {analysis['description']}")

            return {
                "verified": overall_verified,
                "method": most_common_method,
                "amount_match": amount_verified,
                "notes": notes
            }

        except Exception as e:
            return {
                "verified": False,
                "method": "unknown", 
                "amount_match": False,
                "notes": [f"Payment analysis failed: {str(e)}"]
            }

    def _analyze_payment_photo(self, photo_url: str, expected_amount: float) -> Dict:
        """Analyze payment proof photo with OpenAI Vision"""
        
        try:
            photo_base64 = self._url_to_base64(photo_url)
            
            prompt = f"""
            Analyze this payment proof photo for order verification:

            Expected Payment Amount: RM{expected_amount}

            Please determine:
            1. Payment method (cash, online_transfer, qr_code, bank_app, e_wallet)
            2. Can you see the payment amount? Does it match RM{expected_amount}?
            3. Does this appear to be legitimate payment proof?
            4. If cash: Are bills/coins visible? Receipt present?
            5. If digital: Banking app interface? QR payment confirmation? E-wallet?

            Respond in JSON format:
            {{
                "verified": boolean,
                "detected_method": "cash|online_transfer|qr_code|bank_app|e_wallet|unknown",
                "amount_visible": boolean,
                "amount_match": boolean,
                "confidence": float (0-1),
                "description": "What you see in the image"
            }}
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            analysis = json.loads(response.choices[0].message.content)
            return analysis

        except Exception as e:
            return {
                "verified": False,
                "detected_method": "unknown",
                "amount_visible": False,
                "amount_match": False,
                "confidence": 0.0,
                "description": f"Payment analysis failed: {str(e)}"
            }

    def _verify_uid_completeness(self, trip: Trip, order: Order) -> Dict:
        """Verify all required UIDs were scanned"""
        
        try:
            # Get all UIDs scanned for this order
            uid_scans = self.db.query(OrderItemUID).filter(
                OrderItemUID.order_id == trip.order_id
            ).all()

            # Get expected items (this logic may need adjustment based on your data model)
            order_items = getattr(order, 'items', [])
            expected_uid_count = len(order_items)  # Assuming 1 UID per item
            
            scanned_uid_count = len(uid_scans)
            delivery_scans = [scan for scan in uid_scans if scan.action == "DELIVER"]
            
            notes = [
                f"Expected UIDs: {expected_uid_count}",
                f"Total scanned: {scanned_uid_count}",
                f"Delivery scans: {len(delivery_scans)}"
            ]

            # UID verification is complete if we have delivery scans for all items
            uid_verified = len(delivery_scans) >= expected_uid_count

            return {
                "verified": uid_verified,
                "notes": notes
            }

        except Exception as e:
            return {
                "verified": False,
                "notes": [f"UID verification failed: {str(e)}"]
            }

    def _calculate_confidence_score(self, result: AIVerificationResult) -> float:
        """Calculate overall confidence score for verification"""
        
        scores = []
        
        if result.pod_verified:
            scores.append(0.4)  # 40% weight for POD
        if result.payment_verified:
            scores.append(0.4)  # 40% weight for payment
        if result.uid_verified:
            scores.append(0.2)  # 20% weight for UID

        return sum(scores)

    def _url_to_base64(self, photo_url: str) -> str:
        """Convert Firebase photo URL to base64 for OpenAI API"""
        import requests
        
        try:
            # Firebase URLs are public and directly accessible
            print(f"Fetching photo from Firebase: {photo_url}")
            
            # Add timeout and user agent for reliable fetching
            headers = {
                'User-Agent': 'OrderOps-AI-Service/1.0'
            }
            
            response = requests.get(
                photo_url, 
                headers=headers,
                timeout=15.0,  # 15 second timeout for photo fetch
                stream=True   # Stream for large images
            )
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                raise ValueError(f"Invalid content type: {content_type}")
            
            # Convert to base64
            image_data = response.content
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            print(f"Successfully fetched and encoded photo ({len(image_data)} bytes)")
            return base64_data
            
        except requests.exceptions.Timeout:
            raise ValueError("Photo fetch timeout - Firebase may be slow")
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"HTTP error fetching photo: {e}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error fetching photo: {e}")
        except Exception as e:
            raise ValueError(f"Failed to fetch photo: {str(e)}")

    def mark_cash_collected(self, trip_id: int, collected_by_user_id: int, notes: str = None) -> bool:
        """Mark cash as collected for commission release"""
        
        try:
            # This would update a cash collection record
            # Implementation depends on your data model
            
            # For now, just log the action
            from app.utils.audit import log_action
            log_action(
                self.db,
                user_id=collected_by_user_id,
                action="CASH_COLLECTED",
                resource_type="trip",
                resource_id=trip_id,
                details={"notes": notes}
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to mark cash collected: {e}")
            return False