from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal

from ..db import get_session
from ..models import SKU
from ..auth.deps import require_roles, Role, get_current_user
from ..utils.responses import envelope
from ..utils.audit import log_action


router = APIRouter(
    prefix="/skus",
    tags=["skus"],
)


# Pydantic models
class SKUCreateRequest(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: Decimal
    is_serialized: Optional[bool] = False


class SKUUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_serialized: Optional[bool] = None
    is_active: Optional[bool] = None


class SKUResponse(BaseModel):
    id: int
    code: str
    name: str
    category: Optional[str]
    description: Optional[str]
    price: Decimal
    is_serialized: bool
    is_active: bool
    created_at: str
    updated_at: str


@router.get("", response_model=dict)
async def get_all_skus(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get all SKUs"""
    try:
        skus = db.execute(
            select(SKU)
            .where(SKU.is_active == True)
            .order_by(SKU.code)
        ).scalars().all()
        
        sku_list = []
        for sku in skus:
            sku_list.append({
                "id": sku.id,
                "code": sku.code,
                "name": sku.name,
                "category": sku.category,
                "description": sku.description,
                "price": float(sku.price) if sku.price else 0.0,
                "is_serialized": sku.is_serialized,
                "is_active": sku.is_active,
                "created_at": sku.created_at.isoformat() if sku.created_at else None,
                "updated_at": sku.updated_at.isoformat() if sku.updated_at else None,
            })
        
        return envelope(sku_list)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("", response_model=dict)
async def create_sku(
    request: SKUCreateRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Create a new SKU"""
    try:
        # Check if code already exists
        existing = db.execute(
            select(SKU).where(SKU.code == request.code.strip().upper())
        ).scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"SKU code '{request.code}' already exists"
            )
        
        # Create new SKU
        sku = SKU(
            code=request.code.strip().upper(),
            name=request.name.strip(),
            category=request.category.strip() if request.category else None,
            description=request.description.strip() if request.description else None,
            price=request.price,
            is_serialized=request.is_serialized or False,
            is_active=True
        )
        
        db.add(sku)
        db.commit()
        db.refresh(sku)
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="SKU_CREATE",
            resource_type="sku",
            resource_id=sku.id,
            details={
                "code": sku.code,
                "name": sku.name,
                "category": sku.category,
                "price": float(sku.price),
                "is_serialized": sku.is_serialized
            }
        )
        
        return envelope({
            "success": True,
            "sku_id": sku.id,
            "message": f"SKU '{sku.code}' created successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{sku_id}", response_model=dict)
async def get_sku(
    sku_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get a specific SKU by ID"""
    try:
        sku = db.get(SKU, sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        return envelope({
            "id": sku.id,
            "code": sku.code,
            "name": sku.name,
            "category": sku.category,
            "description": sku.description,
            "price": float(sku.price) if sku.price else 0.0,
            "is_serialized": sku.is_serialized,
            "is_active": sku.is_active,
            "created_at": sku.created_at.isoformat() if sku.created_at else None,
            "updated_at": sku.updated_at.isoformat() if sku.updated_at else None,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/{sku_id}", response_model=dict)
async def update_sku(
    sku_id: int,
    request: SKUUpdateRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Update a SKU"""
    try:
        sku = db.get(SKU, sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        # Check if new code conflicts with existing SKU
        if request.code and request.code.strip().upper() != sku.code:
            existing = db.execute(
                select(SKU).where(SKU.code == request.code.strip().upper())
            ).scalar_one_or_none()
            
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"SKU code '{request.code}' already exists"
                )
        
        # Update fields
        if request.code is not None:
            sku.code = request.code.strip().upper()
        if request.name is not None:
            sku.name = request.name.strip()
        if request.category is not None:
            sku.category = request.category.strip() if request.category else None
        if request.description is not None:
            sku.description = request.description.strip() if request.description else None
        if request.price is not None:
            sku.price = request.price
        if request.is_serialized is not None:
            sku.is_serialized = request.is_serialized
        if request.is_active is not None:
            sku.is_active = request.is_active
        
        sku.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(sku)
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="SKU_UPDATE",
            resource_type="sku",
            resource_id=sku.id,
            details={
                "code": sku.code,
                "name": sku.name,
                "changes": request.model_dump(exclude_unset=True)
            }
        )
        
        return envelope({
            "success": True,
            "message": f"SKU '{sku.code}' updated successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{sku_id}", response_model=dict)
async def delete_sku(
    sku_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Delete (deactivate) a SKU"""
    try:
        sku = db.get(SKU, sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        # Soft delete by marking as inactive
        sku.is_active = False
        sku.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="SKU_DELETE",
            resource_type="sku",
            resource_id=sku.id,
            details={"code": sku.code, "name": sku.name}
        )
        
        return envelope({
            "success": True,
            "message": f"SKU '{sku.code}' deleted successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")