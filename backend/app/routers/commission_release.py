"""Commission release management with AI verification"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.auth.firebase import require_roles
from app.db import get_session
from app.models.user import Role
from app.models.trip import Trip
from app.models.order import Order
from app.models.commission_entry import CommissionEntry
from app.services.ai_verification_service import AIVerificationService
from app.services.commission_service import CommissionService
from app.utils.responses import envelope
from app.utils.audit import log_action

router = APIRouter(prefix="/commission-release", tags=["commission-release"])


class CommissionReleaseRequest(BaseModel):
    trip_id: int
    manual_override: bool = False
    cash_collected: bool = False
    notes: Optional[str] = None


class CommissionReleaseResponse(BaseModel):
    success: bool
    trip_id: int
    payment_method: str
    cash_collection_required: bool
    commission_released: bool
    ai_verification: Dict
    message: str


@router.post("/analyze/{trip_id}", response_model=dict)
async def analyze_commission_eligibility(
    trip_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """
    AI analysis of commission release eligibility
    
    Returns payment method detection and cash collection requirements
    """
    
    try:
        # Get trip details
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise HTTPException(404, "Trip not found")
            
        if trip.status != "DELIVERED":
            raise HTTPException(400, "Trip must be DELIVERED before commission analysis")

        # Run AI verification
        ai_service = AIVerificationService(db)
        verification_result = ai_service.verify_commission_release(trip_id)

        # Get existing commission entries
        commission_entries = db.query(CommissionEntry).filter(
            CommissionEntry.trip_id == trip_id
        ).all()

        return envelope({
            "trip_id": trip_id,
            "trip_status": trip.status,
            "ai_verification": verification_result.to_dict(),
            "existing_commissions": len(commission_entries),
            "commission_entries": [
                {
                    "id": entry.id,
                    "driver_id": entry.driver_id,
                    "amount": float(entry.amount),
                    "driver_role": entry.driver_role,
                    "status": entry.status
                }
                for entry in commission_entries
            ]
        })

    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/release", response_model=dict)
async def release_commission(
    request: CommissionReleaseRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """
    Release commission with AI verification and cash collection check
    
    Workflow:
    1. AI detects payment method (cash vs bank transfer)  
    2. If CASH detected: Require cash_collected=True
    3. If BANK TRANSFER: Release immediately
    4. Manual override available for edge cases
    """
    
    try:
        trip = db.query(Trip).filter(Trip.id == request.trip_id).first()
        if not trip:
            raise HTTPException(404, "Trip not found")
            
        if trip.status != "DELIVERED":
            raise HTTPException(400, "Commission can only be released for DELIVERED trips")

        # Run AI verification unless manual override
        ai_verification = None
        payment_method = "unknown"
        cash_collection_required = False
        
        if not request.manual_override:
            ai_service = AIVerificationService(db)
            verification_result = ai_service.verify_commission_release(request.trip_id)
            ai_verification = verification_result.to_dict()
            payment_method = verification_result.payment_method
            cash_collection_required = verification_result.cash_collection_required

            # Check cash collection requirement
            if cash_collection_required and not request.cash_collected:
                return envelope({
                    "success": False,
                    "trip_id": request.trip_id,
                    "payment_method": payment_method,
                    "cash_collection_required": True,
                    "commission_released": False,
                    "ai_verification": ai_verification,
                    "message": "Cash collection required before commission release. Please confirm cash has been collected from driver."
                })

            # If cash detected and collected, mark it as confirmed
            if cash_collection_required and request.cash_collected:
                verification_result.cash_collected_confirmed = True

        # Create commission entries if they don't exist
        existing_entries = db.query(CommissionEntry).filter(
            CommissionEntry.trip_id == request.trip_id
        ).all()

        if not existing_entries:
            # Create new commission entries
            commission_service = CommissionService(db)
            
            # Primary driver commission
            primary_commission = commission_service.create_delivery_commission_entry(
                trip=trip,
                driver_id=trip.driver_id,
                driver_role="primary"
            )
            
            # Secondary driver commission if exists
            if trip.driver_id_2:
                secondary_commission = commission_service.create_delivery_commission_entry(
                    trip=trip,
                    driver_id=trip.driver_id_2,
                    driver_role="secondary"
                )
            
            # Refresh entries list
            existing_entries = db.query(CommissionEntry).filter(
                CommissionEntry.trip_id == request.trip_id
            ).all()

        # Release all pending commission entries for this trip
        released_count = 0
        for entry in existing_entries:
            if entry.status == "EARNED":
                entry.status = "PAID"
                entry.paid_at = datetime.now(timezone.utc)
                entry.notes = f"Released by {current_user.username}. Payment method: {payment_method}. {request.notes or ''}"
                released_count += 1

        # Mark trip as SUCCESS (fully completed)
        trip.status = "SUCCESS"
        
        db.commit()

        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="COMMISSION_RELEASED",
            resource_type="trip",
            resource_id=request.trip_id,
            details={
                "payment_method": payment_method,
                "cash_collected": request.cash_collected,
                "manual_override": request.manual_override,
                "released_entries": released_count,
                "notes": request.notes
            }
        )

        return envelope({
            "success": True,
            "trip_id": request.trip_id,
            "payment_method": payment_method,
            "cash_collection_required": cash_collection_required,
            "commission_released": True,
            "released_entries": released_count,
            "ai_verification": ai_verification,
            "message": f"Commission released successfully for {released_count} entries. Trip marked as SUCCESS."
        })

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Commission release failed: {str(e)}")


@router.get("/pending", response_model=dict)
async def get_pending_commissions(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get all trips with pending commission releases"""
    
    try:
        # Find all DELIVERED trips (ready for commission review)
        delivered_trips = db.query(Trip).filter(
            Trip.status == "DELIVERED"
        ).all()

        pending_commissions = []
        for trip in delivered_trips:
            order = db.query(Order).filter(Order.id == trip.order_id).first()
            
            # Check for existing commission entries
            commission_entries = db.query(CommissionEntry).filter(
                CommissionEntry.trip_id == trip.id
            ).all()
            
            pending_entries = [e for e in commission_entries if e.status == "EARNED"]
            
            if order:
                pending_commissions.append({
                    "trip_id": trip.id,
                    "order_id": trip.order_id,
                    "order_code": order.code,
                    "customer_name": order.customer_name,
                    "total_amount": float(order.total),
                    "delivered_at": trip.delivered_at.isoformat() if trip.delivered_at else None,
                    "primary_driver_id": trip.driver_id,
                    "secondary_driver_id": trip.driver_id_2,
                    "pending_commission_entries": len(pending_entries),
                    "has_pod_photos": bool(trip.pod_photo_urls),
                    "pod_photo_count": len(trip.pod_photo_urls or [])
                })

        return envelope({
            "pending_commissions": pending_commissions,
            "total_count": len(pending_commissions)
        })

    except Exception as e:
        raise HTTPException(500, f"Failed to get pending commissions: {str(e)}")


@router.post("/mark-cash-collected/{trip_id}", response_model=dict)
async def mark_cash_collected(
    trip_id: int,
    notes: str = None,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Mark cash as collected from driver for specific trip"""
    
    try:
        ai_service = AIVerificationService(db)
        success = ai_service.mark_cash_collected(trip_id, current_user.id, notes)
        
        if success:
            return envelope({
                "success": True,
                "trip_id": trip_id,
                "message": "Cash collection marked successfully"
            })
        else:
            raise HTTPException(500, "Failed to mark cash collection")
            
    except Exception as e:
        raise HTTPException(500, f"Cash collection marking failed: {str(e)}")