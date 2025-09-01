"""Clean, simple assignment endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.firebase import get_current_admin_user
from app.db import get_session
from app.models.user import User
from app.services.assignment_service import AssignmentService
from app.utils.responses import envelope

router = APIRouter(prefix="/assignment", tags=["assignment"])


@router.post("/auto-assign")
def auto_assign_orders(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Auto-assign all eligible orders to drivers"""
    try:
        service = AssignmentService(db)
        result = service.auto_assign_all()
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assignment failed: {str(e)}"
        )


@router.get("/status")
def get_assignment_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """Get current assignment status"""
    try:
        service = AssignmentService(db)
        
        orders = service._get_orders_to_assign()
        drivers = service._get_available_drivers()
        
        return envelope({
            "orders_to_assign": len(orders),
            "available_drivers": len(drivers),
            "orders": orders[:5],  # First 5 for preview
            "drivers": drivers[:5]  # First 5 for preview
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )