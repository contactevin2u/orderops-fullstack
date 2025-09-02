"""Upsell management endpoints for admin interface"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, desc

from ..auth.deps import require_roles
from ..db import get_session
from ..models import UpsellRecord, Driver, Order, Trip, Role, User
from ..utils.responses import envelope

router = APIRouter(
    prefix="/upsells", 
    tags=["upsells"],
    dependencies=[Depends(require_roles(Role.ADMIN))]
)


@router.get("", response_model=dict)
def list_upsell_records(
    limit: int = 50,
    offset: int = 0,
    driver_id: int | None = None,
    status: str | None = None,  # PENDING, RELEASED
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN))
):
    """List upsell records with driver and order details"""
    
    query = (
        db.query(UpsellRecord)
        .options(
            joinedload(UpsellRecord.driver),
            joinedload(UpsellRecord.order),
            joinedload(UpsellRecord.trip)
        )
        .order_by(desc(UpsellRecord.created_at))
    )
    
    # Apply filters
    if driver_id:
        query = query.filter(UpsellRecord.driver_id == driver_id)
    
    if status:
        query = query.filter(UpsellRecord.incentive_status == status.upper())
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    upsell_records = query.offset(offset).limit(limit).all()
    
    # Format response
    records = []
    for record in upsell_records:
        # Parse items data from JSON
        items_data = json.loads(record.items_data) if record.items_data else []
        
        records.append({
            "id": record.id,
            "order_id": record.order_id,
            "order_code": record.order.code,
            "driver_id": record.driver_id,
            "driver_name": record.driver.name,
            "trip_id": record.trip_id,
            "original_total": float(record.original_total),
            "new_total": float(record.new_total),
            "upsell_amount": float(record.upsell_amount),
            "driver_incentive": float(record.driver_incentive),
            "incentive_status": record.incentive_status,
            "items_upsold": items_data,
            "upsell_notes": record.upsell_notes,
            "created_at": record.created_at.isoformat(),
            "released_at": record.released_at.isoformat() if record.released_at else None
        })
    
    return envelope({
        "records": records,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    })


@router.post("/{upsell_id}/release", response_model=dict)
def release_upsell_incentive(
    upsell_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN))
):
    """Release/approve driver upsell incentive"""
    
    upsell_record = db.get(UpsellRecord, upsell_id)
    if not upsell_record:
        raise HTTPException(404, "Upsell record not found")
    
    if upsell_record.incentive_status == "RELEASED":
        raise HTTPException(400, "Incentive already released")
    
    # Update status to released
    upsell_record.incentive_status = "RELEASED"
    upsell_record.released_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(upsell_record)
    
    return envelope({
        "success": True,
        "message": f"Released RM{upsell_record.driver_incentive} upsell incentive for driver {upsell_record.driver.name}",
        "released_amount": float(upsell_record.driver_incentive)
    })


@router.get("/summary", response_model=dict)
def upsell_summary_stats(
    start_date: str | None = None,  # YYYY-MM-DD
    end_date: str | None = None,    # YYYY-MM-DD
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN))
):
    """Get upsell summary statistics"""
    
    query = db.query(UpsellRecord)
    
    # Apply date filters if provided
    if start_date:
        start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
        query = query.filter(UpsellRecord.created_at >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        query = query.filter(UpsellRecord.created_at <= end_dt)
    
    upsell_records = query.all()
    
    # Calculate statistics
    total_records = len(upsell_records)
    total_upsell_amount = sum(float(record.upsell_amount) for record in upsell_records)
    total_incentives_pending = sum(
        float(record.driver_incentive) 
        for record in upsell_records 
        if record.incentive_status == "PENDING"
    )
    total_incentives_released = sum(
        float(record.driver_incentive) 
        for record in upsell_records 
        if record.incentive_status == "RELEASED"
    )
    
    # Top performing drivers
    driver_stats = {}
    for record in upsell_records:
        driver_id = record.driver_id
        if driver_id not in driver_stats:
            driver_stats[driver_id] = {
                "driver_name": record.driver.name,
                "upsell_count": 0,
                "total_upsell_amount": 0,
                "total_incentive": 0
            }
        
        driver_stats[driver_id]["upsell_count"] += 1
        driver_stats[driver_id]["total_upsell_amount"] += float(record.upsell_amount)
        driver_stats[driver_id]["total_incentive"] += float(record.driver_incentive)
    
    # Sort by total upsell amount
    top_drivers = sorted(
        driver_stats.values(),
        key=lambda x: x["total_upsell_amount"],
        reverse=True
    )[:5]
    
    return envelope({
        "summary": {
            "total_upsells": total_records,
            "total_upsell_amount": total_upsell_amount,
            "total_incentives_pending": total_incentives_pending,
            "total_incentives_released": total_incentives_released,
            "average_upsell_amount": total_upsell_amount / total_records if total_records > 0 else 0
        },
        "top_drivers": top_drivers
    })