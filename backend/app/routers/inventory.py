from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from typing import List, Optional
import time
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from PIL import Image

from ..db import get_session
from ..models import Order, OrderItemUID, Item, SKU, LorryStock, SKUAlias, Driver, LorryAssignment
from ..models.item import ItemType, ItemStatus
from ..models.order_item_uid import UIDAction
from ..services.inventory_service import InventoryService
from ..services.lorry_inventory_service import LorryInventoryService
from ..auth.deps import require_roles, Role, get_current_user, admin_auth
from ..auth.firebase import driver_auth
from ..core.config import settings
from ..utils.responses import envelope
from ..utils.audit import log_action


router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)

# Pydantic models for request/response
class UIDScanRequest(BaseModel):
    order_id: int
    action: str  # LOAD_OUT, DELIVER, RETURN, REPAIR, SWAP, LOAD_IN
    uid: str
    sku_id: Optional[int] = None  # For manual entry
    notes: Optional[str] = None

class UIDScanResponse(BaseModel):
    success: bool
    uid: str
    action: str
    message: str
    sku_name: Optional[str] = None

class GenerateUIDRequest(BaseModel):
    sku_id: int
    item_type: str  # NEW or RENTAL
    serial_number: Optional[str] = None

class GenerateUIDResponse(BaseModel):
    success: bool
    items: List[dict]  # Generated items with UIDs
    message: str

class GenerateQRRequest(BaseModel):
    uid: Optional[str] = None
    order_id: Optional[int] = None
    content: Optional[str] = None
    size: Optional[int] = 256

class GenerateQRResponse(BaseModel):
    success: bool
    qr_code_base64: str
    format: str
    message: str

class StockLineItem(BaseModel):
    sku_id: int
    counted_quantity: int

class LorryStockUploadRequest(BaseModel):
    date: str  # YYYY-MM-DD
    stock_data: List[StockLineItem]

class LorryStockResponse(BaseModel):
    success: bool
    items_processed: int
    message: str

class SKUResolveRequest(BaseModel):
    name: str
    threshold: Optional[float] = 0.8

class SKUResolveResponse(BaseModel):
    matches: List[dict]
    suggestions: List[str]

class SKUMatch(BaseModel):
    raw: str
    sku_id: Optional[int]
    match_type: str  # EXACT, ALIAS, FUZZY, NONE
    score: float
    suggestions: List[int] = []

class SKUResolveResponse(BaseModel):
    matches: List[SKUMatch]

class SKUAliasRequest(BaseModel):
    sku_id: int
    alias_text: str


@router.post("/orders/{order_id}/uids/issue", response_model=dict)
async def scan_uids_for_delivery(
    order_id: int,
    request: UIDScanRequest,
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """
    Scan UIDs for delivery after POD.
    Behavior depends on UID_INVENTORY_ENABLED and UID_SCAN_REQUIRED_AFTER_POD flags.
    """
    # Feature flag check
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"message": "UID inventory system disabled", "success": True})
    
    # Get order
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate driver
    driver = db.get(Driver, request.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Get serialized items count for this order
    serialized_items_count = _get_serialized_items_count(db, order)
    required_count = serialized_items_count if settings.UID_SCAN_REQUIRED_AFTER_POD else 0
    
    errors = []
    scanned_count = 0
    
    # Initialize inventory service for proper ledger integration
    service = InventoryService(db)
    
    # Process each UID through the inventory service
    for uid in request.uids:
        try:
            # Check if already scanned for this order (idempotent)
            existing = db.execute(
                select(OrderItemUID).where(
                    and_(
                        OrderItemUID.order_id == order_id,
                        OrderItemUID.uid == uid,
                        OrderItemUID.action == UIDAction.ISSUE
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                # Idempotent - already scanned
                scanned_count += 1
                continue
            
            # Use inventory service to process scan (includes ledger recording)
            # For driver scans, recorded_by will be determined by the service (system admin)
            result = service.scan_uid_action(
                order_id=order_id,
                uid=uid,
                action=UIDAction.ISSUE,
                scanned_by=request.driver_id,
                notes=f"Driver delivery scan"
                # recorded_by will be auto-determined for driver scans
            )
            
            if result.get("success"):
                scanned_count += 1
            else:
                errors.append(f"Failed to process UID {uid}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            errors.append(f"Failed to process UID {uid}: {str(e)}")
    
    # Database commit is handled by inventory service
    
    # Log audit action
    try:
        log_action(
            db, 
            user_id=request.driver_id, 
            action="UID_SCAN_ISSUE", 
            resource_type="order", 
            resource_id=order_id,
            details={"uids": request.uids, "scanned_count": scanned_count}
        )
    except Exception as e:
        # Don't fail if audit log fails
        pass
    
    # Check if delivery can be completed
    if settings.UID_SCAN_REQUIRED_AFTER_POD and scanned_count < required_count:
        message = f"Delivery incomplete: {scanned_count}/{required_count} required UIDs scanned"
        success = False
    else:
        message = f"Successfully scanned {scanned_count} UIDs"
        success = True
    
    response = UIDScanResponse(
        success=success,
        scanned_count=scanned_count,
        required_count=required_count,
        message=message,
        errors=errors
    )
    
    return envelope(response.model_dump())


@router.post("/orders/{order_id}/uids/return", response_model=dict)
async def scan_uids_for_return(
    order_id: int,
    request: UIDScanRequest,
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """Scan UIDs for return/collection"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"message": "UID inventory system disabled", "success": True})
    
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    errors = []
    scanned_count = 0
    
    # Initialize inventory service for proper ledger integration
    service = InventoryService(db)
    
    # Process each UID through the inventory service
    for uid in request.uids:
        try:
            # Check if already returned (idempotent)
            existing = db.execute(
                select(OrderItemUID).where(
                    and_(
                        OrderItemUID.order_id == order_id,
                        OrderItemUID.uid == uid,
                        OrderItemUID.action == UIDAction.RETURN
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                scanned_count += 1
                continue
            
            # Use inventory service to process scan (includes ledger recording)
            # For driver scans, recorded_by will be determined by the service (system admin)
            result = service.scan_uid_action(
                order_id=order_id,
                uid=uid,
                action=UIDAction.RETURN,
                scanned_by=request.driver_id,
                notes=f"Driver return scan"
                # recorded_by will be auto-determined for driver scans
            )
            
            if result.get("success"):
                scanned_count += 1
            else:
                errors.append(f"Failed to process UID {uid}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            errors.append(f"Failed to process UID {uid}: {str(e)}")
    
    # Log audit action (database commit is handled by inventory service)
    try:
        log_action(
            db, 
            user_id=request.driver_id, 
            action="UID_SCAN_RETURN", 
            resource_type="order", 
            resource_id=order_id,
            details={"uids": request.uids, "scanned_count": scanned_count}
        )
    except Exception as e:
        # Don't fail if audit log fails
        pass
    
    response = UIDScanResponse(
        success=True,
        scanned_count=scanned_count,
        required_count=0,
        message=f"Successfully recorded {scanned_count} returned UIDs",
        errors=errors
    )
    
    return envelope(response.model_dump())


@router.get("/orders/{order_id}/uids", response_model=dict)
async def get_order_uids(
    order_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get all UIDs associated with an order"""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get all UID records for this order
    uid_records = db.execute(
        select(OrderItemUID, Item, SKU, Driver)
        .join(Item, OrderItemUID.uid == Item.uid)
        .join(SKU, Item.sku_id == SKU.id)
        .join(Driver, OrderItemUID.scanned_by == Driver.id)
        .where(OrderItemUID.order_id == order_id)
        .order_by(OrderItemUID.scanned_at.desc())
    ).all()
    
    uids = []
    for record, item, sku, driver in uid_records:
        uids.append({
            "uid": record.uid,
            "action": record.action,
            "scanned_by": driver.name or f"Driver {driver.id}",
            "scanned_at": record.scanned_at.isoformat(),
            "sku_code": sku.code,
            "sku_name": sku.name,
            "oem_serial": item.oem_serial
        })
    
    return envelope({"uids": uids})


@router.post("/lorry/{driver_id}/stock/upload", response_model=dict)
async def upload_lorry_stock(
    driver_id: int,
    request: LorryStockUploadRequest,
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """Upload daily lorry stock count"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"message": "UID inventory system disabled", "success": True})
    
    # Validate driver
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Parse date
    try:
        as_of_date = datetime.strptime(request.as_of_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Calculate reconciliation data
    reconciliation = _calculate_lorry_reconciliation(db, driver_id, as_of_date, request.lines)
    
    # Upsert lorry stock records
    try:
        for line in request.lines:
            # Check if record exists
            existing = db.execute(
                select(LorryStock).where(
                    and_(
                        LorryStock.driver_id == driver_id,
                        LorryStock.as_of_date == as_of_date,
                        LorryStock.sku_id == line.sku_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                existing.qty_counted = line.qty_counted
                existing.uploaded_at = datetime.utcnow()
                existing.uploaded_by = driver_id
            else:
                stock_record = LorryStock(
                    driver_id=driver_id,
                    as_of_date=as_of_date,
                    sku_id=line.sku_id,
                    qty_counted=line.qty_counted,
                    uploaded_at=datetime.utcnow(),
                    uploaded_by=driver_id
                )
                db.add(stock_record)
        
        db.commit()
        
        log_action(
            db,
            user_id=driver_id,
            action="LORRY_STOCK_UPLOAD",
            resource_type="lorry_stock",
            resource_id=driver_id,
            details={"as_of_date": request.as_of_date, "lines_count": len(request.lines)}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    response = LorryStockResponse(
        success=True,
        reconciliation=reconciliation,
        message=f"Successfully uploaded stock count for {len(request.lines)} SKUs"
    )
    
    return envelope(response.model_dump())


@router.get("/lorry/{driver_id}/stock", response_model=dict)
async def get_lorry_stock_driver(
    driver_id: int,
    date: str,  # REQUIRED
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """Get lorry stock snapshot for a specific date (driver authentication)"""
    return _lorry_stock_core(db=db, driver_id=driver_id, date=date)


@router.get("/admin/lorry/{driver_id}/stock", response_model=dict)
async def get_lorry_stock_admin(
    driver_id: int,
    date: str,  # REQUIRED
    db: Session = Depends(get_session),
    current_user = Depends(admin_auth)
):
    """Admin alias for lorry stock snapshot (admin authentication)"""
    return _lorry_stock_core(db=db, driver_id=driver_id, date=date)


def _lorry_stock_core(db: Session, driver_id: int, date: str):
    """Core lorry stock logic shared by both driver and admin endpoints"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({
            "date": datetime.utcnow().date().isoformat(),
            "driver_id": driver_id,      # Backend snake_case
            "driverId": driver_id,       # Driver app camelCase
            "items": [],
            "total_expected": 0,         # Backend snake_case
            "totalExpected": 0,          # Driver app camelCase
            "total_scanned": 0,          # Backend snake_case
            "totalScanned": 0,           # Driver app camelCase
            "total_variance": 0,         # Backend snake_case
            "totalVariance": 0,          # Driver app camelCase
            "message": "UID inventory system disabled"
        })
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get driver's current lorry assignment
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver_id,
                LorryAssignment.assignment_date == target_date
            )
        )
    ).scalar_one_or_none()
    
    if not assignment:
        # No assignment found, return empty stock
        response_data = {
            "date": target_date.isoformat(),
            "driver_id": driver_id,  # Keep backend snake_case for consistency
            "driverId": driver_id,   # Add camelCase for driver app compatibility
            "items": [],
            "total_expected": 0,     # Backend snake_case
            "totalExpected": 0,      # Driver app camelCase
            "total_scanned": 0,      # Backend snake_case  
            "totalScanned": 0,       # Driver app camelCase
            "total_variance": 0,     # Backend snake_case
            "totalVariance": 0,      # Driver app camelCase
            "message": "No lorry assignment found for this date"
        }
        return envelope(response_data)
    
    # Use lorry inventory service to get current stock
    inventory_service = LorryInventoryService(db)
    current_uids = inventory_service.get_current_stock(assignment.lorry_id, target_date)
    
    # Group UIDs by SKU for display - parse UID format directly
    sku_counts = {}
    items = []
    
    for uid in current_uids:
        # Parse SKU info from UID format (like frontend endpoint)
        sku_info = uid.split('|')[1] if '|' in uid and len(uid.split('|')) > 1 else "UNKNOWN"
        sku_key = sku_info.replace('SKU:', '') if ':' in sku_info else sku_info
        
        # Try to get actual SKU details from database
        sku_id = None
        sku_name = sku_key
        sku_code = sku_key
        
        try:
            if sku_key.isdigit():
                sku = db.get(SKU, int(sku_key))
                if sku:
                    sku_id = sku.id
                    sku_name = sku.name
                    sku_code = sku.code
        except:
            pass  # Use parsed values as fallback
        
        if sku_key not in sku_counts:
            sku_counts[sku_key] = {
                "sku_id": sku_id or 0,
                "sku_name": sku_name,
                "sku_code": sku_code,
                "count": 0,
                "uids": []
            }
        
        sku_counts[sku_key]["count"] += 1
        sku_counts[sku_key]["uids"].append(uid)
    
    # Convert to items format expected by driver app
    for sku_data in sku_counts.values():
        items.append({
            "sku_id": sku_data["sku_id"],        # Backend snake_case
            "skuId": sku_data["sku_id"],         # Driver app camelCase
            "sku_name": sku_data["sku_name"],    # Backend snake_case
            "skuName": sku_data["sku_name"],     # Driver app camelCase
            "expected_count": sku_data["count"], # Backend snake_case
            "expectedCount": sku_data["count"],  # Driver app camelCase
            "scanned_count": sku_data["count"],  # Backend snake_case
            "scannedCount": sku_data["count"],   # Driver app camelCase
            "variance": 0,                       # No variance for current stock view
            "uids": sku_data["uids"]             # Include UIDs for scanning
        })
    
    total_scanned = len(current_uids)
    
    # Match the LorryStockResponse structure expected by the driver app
    response_data = {
        "date": target_date.isoformat(),
        "driver_id": driver_id,      # Backend snake_case
        "driverId": driver_id,       # Driver app camelCase
        "lorry_id": assignment.lorry_id,
        "items": items,
        "total_expected": len(current_uids),  # Backend snake_case
        "totalExpected": len(current_uids),   # Driver app camelCase
        "total_scanned": len(current_uids),   # Backend snake_case
        "totalScanned": len(current_uids),    # Driver app camelCase
        "total_variance": 0,                  # Backend snake_case
        "totalVariance": 0,                   # Driver app camelCase
        "current_uids": current_uids,         # Include for verification workflow
        "message": f"Current stock for lorry {assignment.lorry_id}"
    }
    
    return envelope(response_data)


def _calculate_lorry_reconciliation(db: Session, driver_id: int, as_of_date: date, current_lines: List[StockLineItem]) -> dict:
    """Calculate reconciliation between expected and counted stock"""
    reconciliation = {
        "as_of_date": as_of_date.isoformat(),
        "driver_id": driver_id,
        "skus": [],
        "total_variance": 0
    }
    
    # Get yesterday's stock
    yesterday = as_of_date - timedelta(days=1)
    yesterday_stock = db.execute(
        select(LorryStock).where(
            and_(
                LorryStock.driver_id == driver_id,
                LorryStock.as_of_date == yesterday
            )
        )
    ).all()
    
    yesterday_by_sku = {stock.sku_id: stock.qty_counted for stock in yesterday_stock}
    
    # Get yesterday's issued UIDs (deduct from expected count)
    issued_yesterday = db.execute(
        select(
            Item.sku_id,
            func.count(OrderItemUID.uid).label("issued_count")
        )
        .join(Item, OrderItemUID.uid == Item.uid)
        .where(
            and_(
                OrderItemUID.scanned_by == driver_id,
                OrderItemUID.action == "ISSUE",
                func.date(OrderItemUID.scanned_at) == yesterday
            )
        )
        .group_by(Item.sku_id)
    ).all()
    
    issued_by_sku = {row[0]: row[1] for row in issued_yesterday}
    
    # Get yesterday's returned UIDs (add to expected count)
    returned_yesterday = db.execute(
        select(
            Item.sku_id,
            func.count(OrderItemUID.uid).label("returned_count")
        )
        .join(Item, OrderItemUID.uid == Item.uid)
        .where(
            and_(
                OrderItemUID.scanned_by == driver_id,
                OrderItemUID.action == "RETURN",
                func.date(OrderItemUID.scanned_at) == yesterday
            )
        )
        .group_by(Item.sku_id)
    ).all()
    
    returned_by_sku = {row[0]: row[1] for row in returned_yesterday}
    
    # Calculate variance for each SKU
    current_by_sku = {line.sku_id: line.qty_counted for line in current_lines}
    all_sku_ids = set(yesterday_by_sku.keys()) | set(current_by_sku.keys()) | set(issued_by_sku.keys()) | set(returned_by_sku.keys())
    
    for sku_id in all_sku_ids:
        yesterday_count = yesterday_by_sku.get(sku_id, 0)
        issued = issued_by_sku.get(sku_id, 0)
        returned = returned_by_sku.get(sku_id, 0)
        current_count = current_by_sku.get(sku_id, 0)
        
        expected = yesterday_count - issued + returned
        variance = current_count - expected
        
        # Get SKU info
        sku = db.get(SKU, sku_id)
        sku_code = sku.code if sku else f"SKU_{sku_id}"
        
        reconciliation["skus"].append({
            "sku_id": sku_id,
            "sku_code": sku_code,
            "yesterday_count": yesterday_count,
            "issued_yesterday": issued,
            "returned_yesterday": returned,
            "expected_today": expected,
            "counted_today": current_count,
            "variance": variance
        })
        
        reconciliation["total_variance"] += abs(variance)
    
    return reconciliation


@router.post("/sku/resolve", response_model=dict)
async def resolve_sku_names(
    request: SKUResolveRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Resolve raw product names to SKU IDs using exact, alias, and fuzzy matching"""
    matches = []
    
    for raw_name in request.raw_names:
        match = _resolve_single_sku_name(db, raw_name)
        matches.append(match)
    
    response = SKUResolveResponse(matches=matches)
    return envelope(response.model_dump())


@router.post("/sku/alias", response_model=dict)
async def create_sku_alias(
    request: SKUAliasRequest,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Create a new SKU alias for name matching"""
    # Validate SKU exists
    sku = db.get(SKU, request.sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    # Check if alias already exists
    existing = db.execute(
        select(SKUAlias).where(
            and_(
                SKUAlias.sku_id == request.sku_id,
                SKUAlias.alias_text.ilike(request.alias_text.strip())
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        return envelope({"message": "Alias already exists", "alias_id": existing.id})
    
    try:
        alias = SKUAlias(
            sku_id=request.sku_id,
            alias_text=request.alias_text.strip().lower(),
            weight=1,
            created_at=datetime.utcnow()
        )
        db.add(alias)
        db.commit()
        
        log_action(
            db,
            user_id=current_user.id,
            action="SKU_ALIAS_CREATE",
            resource_type="sku_alias",
            resource_id=alias.id,
            details={"sku_id": request.sku_id, "alias_text": request.alias_text}
        )
        
        return envelope({"message": "Alias created successfully", "alias_id": alias.id})
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _resolve_single_sku_name(db: Session, raw_name: str) -> SKUMatch:
    """Resolve a single raw name to SKU using multiple strategies"""
    raw_name = raw_name.strip()
    
    # Strategy 1: Exact SKU code match
    exact_sku = db.execute(
        select(SKU).where(SKU.code.ilike(raw_name))
    ).scalar_one_or_none()
    
    if exact_sku:
        return SKUMatch(
            raw=raw_name,
            sku_id=exact_sku.id,
            match_type="EXACT",
            score=1.0,
            suggestions=[]
        )
    
    # Strategy 2: Alias match
    alias_match = db.execute(
        select(SKUAlias, SKU)
        .join(SKU, SKUAlias.sku_id == SKU.id)
        .where(SKUAlias.alias_text.ilike(f"%{raw_name.lower()}%"))
        .order_by(SKUAlias.weight.desc())
    ).first()
    
    if alias_match:
        alias, sku = alias_match
        return SKUMatch(
            raw=raw_name,
            sku_id=sku.id,
            match_type="ALIAS",
            score=0.9,
            suggestions=[]
        )
    
    # Strategy 3: Fuzzy matching
    all_skus = db.execute(select(SKU).where(SKU.is_active == True)).scalars().all()
    
    try:
        from rapidfuzz import fuzz
        
        best_match = None
        best_score = 0
        suggestions = []
        
        for sku in all_skus:
            # Check against SKU name and code
            name_score = fuzz.token_set_ratio(raw_name.lower(), sku.name.lower()) / 100
            code_score = fuzz.token_set_ratio(raw_name.lower(), sku.code.lower()) / 100
            
            max_score = max(name_score, code_score)
            
            if max_score >= 0.85:  # High threshold for fuzzy matching
                if max_score > best_score:
                    best_match = sku
                    best_score = max_score
                
                if max_score >= 0.75:  # Add to suggestions
                    suggestions.append(sku.id)
        
        if best_match:
            return SKUMatch(
                raw=raw_name,
                sku_id=best_match.id,
                match_type="FUZZY",
                score=best_score,
                suggestions=suggestions[:5]  # Limit to top 5 suggestions
            )
    
    except ImportError:
        # rapidfuzz not available, skip fuzzy matching
        pass
    
    # No match found
    # Still provide some suggestions based on partial name matching
    partial_matches = db.execute(
        select(SKU)
        .where(
            and_(
                SKU.is_active == True,
                SKU.name.ilike(f"%{raw_name}%")
            )
        )
        .limit(5)
    ).scalars().all()
    
    suggestions = [sku.id for sku in partial_matches]
    
    return SKUMatch(
        raw=raw_name,
        sku_id=None,
        match_type="NONE",
        score=0.0,
        suggestions=suggestions
    )


def _get_serialized_items_count(db: Session, order: Order) -> int:
    """Get the count of serialized items in an order"""
    # This is a simplified version - in reality you'd check order items against SKU is_serialized flag
    # For now, assume certain categories require UID scanning
    serialized_categories = ["BED", "WHEELCHAIR", "OXYGEN"]
    
    count = 0
    for item in order.items:
        if item.category and item.category.upper() in serialized_categories:
            count += int(item.qty or 1)
    
    return count


# Enhanced UID System Endpoints - Keep simple workflow integration

@router.get("/config", response_model=dict)
async def get_inventory_config():
    """Get inventory system configuration - integrates with existing commission workflow"""
    return envelope({
        "uid_inventory_enabled": settings.UID_INVENTORY_ENABLED,
        "uid_scan_required_after_pod": settings.UID_SCAN_REQUIRED_AFTER_POD,
        "inventory_mode": settings.uid_inventory_mode
    })


@router.post("/uid/scan", response_model=dict)
async def scan_uid(
    request: UIDScanRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Enhanced UID scanning with extended actions and real-time lorry inventory updates"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"success": True, "message": "UID inventory disabled"})
    
    try:
        from ..services.lorry_inventory_service import LorryInventoryService
        
        service = InventoryService(db)
        lorry_service = LorryInventoryService(db)
        
        # Map string action to enum
        action_map = {
            "LOAD_OUT": UIDAction.LOAD_OUT,
            "DELIVER": UIDAction.DELIVER,
            "RETURN": UIDAction.RETURN,
            "REPAIR": UIDAction.REPAIR,
            "SWAP": UIDAction.SWAP,
            "LOAD_IN": UIDAction.LOAD_IN,
            "ISSUE": UIDAction.ISSUE  # Legacy compatibility
        }
        
        if request.action not in action_map:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        action_enum = action_map[request.action]
        
        result = service.scan_uid_action(
            order_id=request.order_id,
            uid=request.uid,
            action=action_enum,
            scanned_by=current_user.id,
            sku_id=request.sku_id,
            notes=request.notes,
            recorded_by=current_user.id  # Admin who is recording this scan
        )
        
        # Enhanced: Also update lorry inventory for real-time variance detection
        # Get driver's current lorry assignment if this is a driver scan
        driver = None
        if hasattr(current_user, 'driver_id'):
            driver = db.get(Driver, current_user.driver_id)
        elif hasattr(current_user, 'role') and current_user.role == 'DRIVER':
            driver = db.execute(
                select(Driver).where(Driver.user_id == current_user.id)
            ).scalar_one_or_none()
        
        if driver:
            today = date.today()
            assignment = db.execute(
                select(LorryAssignment).where(
                    and_(
                        LorryAssignment.driver_id == driver.id,
                        LorryAssignment.assignment_date == today
                    )
                )
            ).scalar_one_or_none()

            if not assignment or not assignment.lorry_id:
                raise HTTPException(status_code=409, detail="No lorry assignment for today. Please contact dispatcher.")

            # Map driver action to lorry actions expected by the service
            # (Your earlier map already normalized request.action)
            uid_actions = [{
                "action": request.action,  # "DELIVER" / "RETURN" / "REPAIR" / "SWAP" etc
                "uid": request.uid,
                "notes": request.notes or f"Order {request.order_id} - {request.action}"
            }]

            lorry_result = lorry_service.process_delivery_actions(
                lorry_id=assignment.lorry_id,
                order_id=request.order_id,
                driver_id=driver.id,
                admin_user_id=current_user.id,
                uid_actions=uid_actions,
                ensure_in_lorry=True
            )

            result["lorry_tracking"] = {
                "lorry_id": assignment.lorry_id,
                "transaction_created": lorry_result.get("success", False),
                "message": lorry_result.get("message", ""),
                "errors": lorry_result.get("errors", [])
            }

            # If delivery failed due to membership, surface 409 so driver can correct
            if not lorry_result.get("success") and lorry_result.get("errors"):
                raise HTTPException(status_code=409, detail={"lorry_errors": lorry_result["errors"]})
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action=f"UID_SCAN_{request.action}",
            resource_type="order",
            resource_id=request.order_id,
            details={"uid": request.uid, "action": request.action}
        )
        
        return envelope(result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-uid", response_model=dict)
async def generate_uid(
    request: GenerateUIDRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Generate UIDs for new items"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"success": True, "message": "UID inventory disabled"})
    
    try:
        # Get SKU info
        sku = db.get(SKU, request.sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        # Map string to enum
        item_type = ItemType.NEW if request.item_type.upper() == "NEW" else ItemType.RENTAL
        
        # Generate simple admin UID format: SKU001-ADMIN-20240906-001
        sku_code = f"SKU{sku.id:03d}"
        today_str = datetime.utcnow().strftime("%Y%m%d")
        
        # Generate UIDs atomically with retry on conflicts
        items = []
        copies = 2 if item_type == ItemType.NEW else 1
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Get next sequence number for today
                existing_count = db.execute(
                    select(func.count(Item.uid)).where(
                        Item.uid.like(f"{sku_code}-ADMIN-{today_str}-%")
                    )
                ).scalar() or 0
                
                items = []  # Reset items list on retry
                
                for copy_num in range(1, copies + 1):
                    seq_num = existing_count + copy_num
                    if copies > 1:
                        uid = f"{sku_code}-ADMIN-{today_str}-{seq_num:03d}-C{copy_num}"
                    else:
                        uid = f"{sku_code}-ADMIN-{today_str}-{seq_num:03d}"
                    
                    item = Item(
                        uid=uid,
                        sku_id=request.sku_id,
                        item_type=item_type,
                        copy_number=copy_num if copies > 1 else None,
                        oem_serial=request.serial_number,
                        status=ItemStatus.WAREHOUSE,
                        created_at=datetime.utcnow()
                    )
                    items.append(item)
                    db.add(item)
                
                db.commit()
                break  # Success, exit retry loop
                
            except IntegrityError as e:
                db.rollback()
                if attempt < max_retries - 1:
                    # Retry on unique constraint violation with exponential backoff
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                else:
                    # Max retries exceeded
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to generate unique UID after multiple attempts. Please try again."
                    )
            except Exception as e:
                db.rollback()
                raise  # Re-raise non-recoverable errors immediately
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="UID_GENERATE",
            resource_type="sku",
            resource_id=request.sku_id,
            details={"item_type": request.item_type, "count": len(items)}
        )
        
        item_data = [{
            "uid": item.uid,
            "type": item.item_type.value,
            "copy_number": item.copy_number,
            "serial": item.oem_serial
        } for item in items]
        
        return envelope({
            "success": True,
            "items": item_data,
            "message": f"Generated {len(items)} UID(s) for {item_type.value} item"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/uid-summary", response_model=dict)
async def get_order_uid_summary(
    order_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get UID scan summary for an order - integrates with commission checking"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({
            "order_id": order_id,
            "uids": [],
            "total_issued": 0,
            "total_returned": 0
        })
    
    try:
        service = InventoryService(db)
        result = service.get_order_uids(order_id)
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sku/resolve-v2", response_model=dict)
async def resolve_sku_v2(
    request: SKUResolveRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Resolve SKU name using enhanced matching"""
    try:
        service = InventoryService(db)
        matches = service.resolve_sku_name(request.name, request.threshold)
        suggestions = service.get_sku_suggestions(request.name)
        
        return envelope({
            "matches": matches,
            "suggestions": suggestions
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sku/alias-v2", response_model=dict)
async def add_sku_alias_v2(
    request: dict,  # {sku_id: int, alias: str}
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Add SKU alias for better name matching"""
    try:
        service = InventoryService(db)
        result = service.add_sku_alias(request["sku_id"], request["alias"])
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="SKU_ALIAS_ADD",
            resource_type="sku",
            resource_id=request["sku_id"],
            details={"alias": request["alias"]}
        )
        
        return envelope(result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drivers/{driver_id}/stock-status", response_model=dict)
async def stock_status_driver(
    driver_id: int,
    date: str,  # REQUIRED
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """Driver-scoped stock status endpoint (driver authentication required)"""
    return _stock_status_core(db=db, driver_id=driver_id, date=date)


@router.get("/admin/drivers/{driver_id}/stock-status", response_model=dict)
async def stock_status_admin(
    driver_id: int,
    date: str,  # REQUIRED
    db: Session = Depends(get_session),
    current_user = Depends(admin_auth)
):
    """Admin alias for stock status endpoint (admin authentication required)"""
    return _stock_status_core(db=db, driver_id=driver_id, date=date)


def _stock_status_core(db: Session, driver_id: int, date: str):
    """Core stock status logic shared by both driver and admin endpoints"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")

    # 1) Find assignment
    assignment = db.execute(
        select(LorryAssignment).where(
            and_(
                LorryAssignment.driver_id == driver_id,
                LorryAssignment.assignment_date == target_date
            )
        )
    ).scalar_one_or_none()

    if not assignment:
        return envelope({
            "date": target_date.isoformat(),
            "driver_id": driver_id,
            "items": [],
            "stock_items": [],  # Backward compatibility
            "total_expected": 0,
            "total_scanned": 0,
            "total_variance": 0,
            "total_items": 0,  # Backward compatibility
            "message": "No lorry assignment on this date",
            "holds": []
        })

    # 2) Event-sourced expected (same as lorry endpoint)
    lis = LorryInventoryService(db)
    expected_uids = lis.get_current_stock(assignment.lorry_id, target_date)

    # Group by SKU (reuse your parsing)
    buckets = {}
    for uid in expected_uids:
        sku_info = uid.split('|')[1] if '|' in uid and len(uid.split('|')) > 1 else "UNKNOWN"
        sku_key = sku_info.replace('SKU:', '') if ':' in sku_info else sku_info
        key = sku_key or "UNKNOWN"
        buckets.setdefault(key, {"sku_name": key, "count": 0, "items": []})
        buckets[key]["count"] += 1
        buckets[key]["items"].append({"uid": uid, "serial": "N/A", "type": "UNKNOWN", "copy_number": buckets[key]["count"]})

    items = list(buckets.values())
    total_expected = sum(x["count"] for x in items)

    # 3) Morning verification (if exists on that date)
    from ..models.lorry_assignment import LorryStockVerification, DriverHold
    verification = db.execute(
        select(LorryStockVerification).where(
            and_(
                LorryStockVerification.driver_id == driver_id,
                LorryStockVerification.verification_date == target_date
            )
        )
    ).scalar_one_or_none()

    total_scanned = verification.total_scanned if verification else 0
    total_variance = total_scanned - total_expected

    # 4) Holds (active)
    holds = db.query(DriverHold).filter(
        DriverHold.driver_id == driver_id,
        DriverHold.status == "ACTIVE"
    ).all()

    holds_view = [{"id": h.id, "reason": h.reason, "description": h.description} for h in holds]

    return envelope({
        "date": target_date.isoformat(),
        "driver_id": driver_id,
        "lorry_id": assignment.lorry_id,
        "items": items,
        "stock_items": items,  # Backward compatibility
        "total_expected": total_expected,
        "total_scanned": total_scanned,
        "total_variance": total_variance,
        "total_items": total_expected,  # Backward compatibility
        "message": f"Stock status for {assignment.lorry_id}",
        "holds": holds_view
    })


@router.post("/lorry-stock/upload", response_model=dict)
async def upload_lorry_stock_v2(
    request: LorryStockUploadRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Upload lorry stock count - enhanced with UID reconciliation"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"success": True, "message": "UID inventory disabled"})
    
    try:
        # Parse date
        upload_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        
        # Delete existing records for this date
        db.execute(
            select(LorryStock).where(
                and_(
                    LorryStock.driver_id == current_user.id,
                    LorryStock.as_of_date == upload_date
                )
            )
        )
        
        # Add new records
        items_processed = 0
        for item in request.stock_data:
            stock_record = LorryStock(
                driver_id=current_user.id,
                as_of_date=upload_date,
                sku_id=item.sku_id,
                qty_counted=item.counted_quantity,
                uploaded_by=current_user.id
            )
            db.add(stock_record)
            items_processed += 1
        
        db.commit()
        
        # Log audit action
        log_action(
            db,
            user_id=current_user.id,
            action="LORRY_STOCK_UPLOAD",
            resource_type="driver",
            resource_id=current_user.id,
            details={"date": request.date, "items": items_processed}
        )
        
        return envelope({
            "success": True,
            "items_processed": items_processed,
            "message": f"Successfully uploaded stock for {request.date}"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uid/{uid}/details", response_model=dict)
async def get_uid_details(
    uid: str,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get comprehensive details for a specific UID including full history"""
    # Get basic item details
    item = db.execute(
        select(Item, SKU)
        .join(SKU, Item.sku_id == SKU.id)
        .where(Item.uid == uid)
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"UID {uid} not found")
    
    item_obj, sku = item
    
    # Get current driver if any
    current_driver = None
    if item_obj.current_driver_id:
        driver = db.get(Driver, item_obj.current_driver_id)
        if driver:
            current_driver = {
                "id": driver.id,
                "name": driver.name,
                "employee_id": driver.employee_id
            }
    
    # Get stock transaction history
    from ..models import LorryStockTransaction, User
    
    # Get all stock transactions for this UID
    stock_transactions = db.execute(
        select(LorryStockTransaction, User)
        .join(User, LorryStockTransaction.admin_user_id == User.id, isouter=True)
        .where(LorryStockTransaction.uid == uid)
        .order_by(LorryStockTransaction.transaction_date.desc())
    ).all()
    
    stock_history = []
    for transaction, user in stock_transactions:
        stock_history.append({
            "id": transaction.id,
            "action": transaction.action,
            "lorry_id": transaction.lorry_id,
            "order_id": transaction.order_id,
            "driver_id": transaction.driver_id,
            "admin_user": user.username if user else "System",
            "notes": transaction.notes,
            "transaction_date": transaction.transaction_date.isoformat(),
            "created_at": transaction.created_at.isoformat()
        })
    
    # Get order/delivery history
    order_actions = db.execute(
        select(OrderItemUID, Order, Driver)
        .join(Order, OrderItemUID.order_id == Order.id)
        .join(Driver, OrderItemUID.scanned_by == Driver.id, isouter=True)
        .where(OrderItemUID.uid == uid)
        .order_by(OrderItemUID.scanned_at.desc())
    ).all()
    
    delivery_history = []
    for uid_action, order, driver in order_actions:
        delivery_history.append({
            "id": uid_action.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "action": uid_action.action,
            "driver_name": driver.name if driver else None,
            "notes": uid_action.notes,
            "scanned_at": uid_action.created_at.isoformat()
        })
    
    # Determine current location
    current_location = "Unknown"
    current_lorry = None
    
    if stock_history:
        # Find the latest stock transaction to determine current location
        latest_stock = stock_history[0]
        if latest_stock["action"] in ["LOAD", "COLLECTION"]:
            current_location = f"Lorry {latest_stock['lorry_id']}"
            current_lorry = latest_stock['lorry_id']
        elif latest_stock["action"] in ["UNLOAD"]:
            current_location = "Warehouse"
        elif latest_stock["action"] in ["DELIVERY"]:
            current_location = "Delivered"
    
    response_data = {
        "uid": uid,
        "sku": {
            "id": sku.id,
            "code": sku.code,
            "name": sku.name,
            "category": sku.category,  # Use category instead of non-existent type field
            "is_serialized": sku.is_serialized
        },
        "item": {
            "uid": item_obj.uid,
            "status": item_obj.status.value,
            "item_type": item_obj.item_type.value,
            "oem_serial": item_obj.oem_serial,
            "created_at": item_obj.created_at.isoformat()
        },
        "current_location": current_location,
        "current_lorry": current_lorry,
        "current_driver": current_driver,
        "stock_history": stock_history,
        "delivery_history": delivery_history,
        "total_transactions": len(stock_history) + len(delivery_history)
    }
    
    return envelope(response_data)


@router.get("/uid/search", response_model=dict)
async def search_uids(
    query: str,
    limit: int = 50,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Search UIDs by various criteria"""
    if len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    # Search UIDs by pattern
    uid_results = db.execute(
        select(Item, SKU)
        .join(SKU, Item.sku_id == SKU.id)
        .where(Item.uid.ilike(f"%{query}%"))
        .limit(limit)
    ).all()
    
    results = []
    for item, sku in uid_results:
        # Get latest stock location
        from ..models import LorryStockTransaction
        latest_transaction = db.execute(
            select(LorryStockTransaction)
            .where(LorryStockTransaction.uid == item.uid)
            .order_by(LorryStockTransaction.transaction_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        current_location = "Unknown"
        if latest_transaction:
            if latest_transaction.action in ["LOAD", "COLLECTION"]:
                current_location = f"Lorry {latest_transaction.lorry_id}"
            elif latest_transaction.action in ["UNLOAD"]:
                current_location = "Warehouse"
            elif latest_transaction.action in ["DELIVERY"]:
                current_location = "Delivered"
        
        results.append({
            "uid": item.uid,
            "sku_code": sku.code,
            "sku_name": sku.name,
            "status": item.status.value,
            "current_location": current_location,
            "created_at": item.created_at.isoformat()
        })
    
    return envelope({
        "query": query,
        "results": results,
        "total_found": len(results),
        "limit_applied": limit
    })


@router.post("/bulk-generate", response_model=dict)
async def bulk_generate_uids(
    request: dict,  # Use dict to handle flexible input
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Generate multiple UIDs in bulk for a specific SKU and driver"""
    try:
        # Extract request data
        sku_id = request.get('sku_id')
        driver_id = request.get('driver_id')
        item_type = request.get('item_type', 'RENTAL')
        quantity = request.get('quantity', 1)
        generation_date = request.get('generation_date')
        notes = request.get('notes', '')
        
        # Validation
        if not sku_id or not driver_id:
            raise HTTPException(status_code=400, detail="SKU ID and Driver ID are required")
        
        if quantity < 1 or quantity > 100:
            raise HTTPException(status_code=400, detail="Quantity must be between 1 and 100")
        
        # Get SKU and Driver info
        sku = db.get(SKU, sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        driver = db.get(Driver, driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        # Parse generation date
        if generation_date:
            try:
                gen_date = datetime.strptime(generation_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            gen_date = date.today()
        
        # Use inventory service for UID generation
        service = InventoryService(db)
        generated_uids = []
        errors = []
        
        # Generate UIDs for each item
        for i in range(quantity):
            try:
                # Create a temporary item type enum
                from ..models.item import ItemType
                item_type_enum = ItemType.NEW if item_type == 'NEW' else ItemType.RENTAL
                
                # Generate UID(s) for this item
                uids = service.generate_uid_for_item(
                    sku_id=sku_id,
                    driver_id=driver_id,
                    item_type=item_type_enum,
                    generation_date=gen_date
                )
                
                if isinstance(uids, list):
                    generated_uids.extend(uids)
                else:
                    generated_uids.append(uids)
                    
            except Exception as e:
                errors.append(f"Failed to generate UID for item {i+1}: {str(e)}")
        
        # Log audit action
        from ..services.audit_service import log_action
        log_action(
            db,
            user_id=current_user.id,
            action="BULK_UID_GENERATION",
            resource_type="inventory",
            resource_id=sku_id,
            details={
                "sku_code": sku.code,
                "driver_id": driver_id,
                "driver_name": driver.name,
                "item_type": item_type,
                "quantity_requested": quantity,
                "quantity_generated": len(generated_uids),
                "generation_date": gen_date.isoformat(),
                "notes": notes
            }
        )
        
        return envelope({
            "success": len(errors) == 0,
            "generated_uids": generated_uids,
            "total_generated": len(generated_uids),
            "errors": errors,
            "generation_details": {
                "sku_code": sku.code,
                "driver_name": driver.name,
                "item_type": item_type,
                "quantity": quantity,
                "date": gen_date.isoformat()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk UID generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skus", response_model=dict)
async def get_skus(
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get all available SKUs for UID generation"""
    skus = db.execute(select(SKU).order_by(SKU.code)).scalars().all()
    
    sku_list = []
    for sku in skus:
        sku_list.append({
            "id": sku.id,
            "code": sku.code,
            "name": sku.name,
            "type": sku.type.value if sku.type else None,
            "description": sku.description
        })
    
    return envelope({
        "skus": sku_list,
        "total": len(sku_list)
    })


class QRCodeRequest(BaseModel):
    uid: Optional[str] = None
    order_id: Optional[int] = None
    content: Optional[str] = None
    size: Optional[int] = 200


class QRCodeResponse(BaseModel):
    success: bool
    qr_code_base64: str
    format: str
    message: str


@router.post("/generate-qr", response_model=dict)
async def generate_qr_code(
    request: QRCodeRequest,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Generate QR code for UID or custom content"""
    try:
        # Determine content to encode
        if request.content:
            content = request.content
        elif request.uid:
            content = f"UID:{request.uid}"
        elif request.order_id:
            content = f"ORDER:{request.order_id}"
        else:
            raise HTTPException(status_code=400, detail="Must provide content, uid, or order_id")
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=max(1, request.size // 25),  # Scale box size based on requested size
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize to requested size
        if request.size and request.size > 0:
            img = img.resize((request.size, request.size), Image.LANCZOS)
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return envelope({
            "success": True,
            "qr_code_base64": f"data:image/png;base64,{qr_code_base64}",
            "format": "PNG",
            "message": "QR code generated successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR code generation failed: {str(e)}")


@router.get("/uid/{uid}/ledger", response_model=dict)
async def get_uid_ledger_history(
    uid: str,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get comprehensive ledger history for a specific UID"""
    try:
        from ..services.uid_ledger_service import UIDLedgerService
        
        service = UIDLedgerService(db)
        history = service.get_uid_history(uid)
        
        return envelope({
            "uid": uid,
            "total_entries": len(history),
            "history": history
        })
        
    except Exception as e:
        logger.error(f"Error fetching UID ledger history for {uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch UID ledger history: {str(e)}")


@router.get("/ledger/audit-trail", response_model=dict)
async def get_ledger_audit_trail(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    uid: Optional[str] = None,
    action: Optional[str] = None,
    scanner_id: Optional[int] = None,
    order_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Get audit trail for medical device traceability reporting"""
    try:
        from ..services.uid_ledger_service import UIDLedgerService
        from ..models.uid_ledger import UIDAction
        
        service = UIDLedgerService(db)
        
        # Parse dates
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        # Parse action enum
        parsed_action = None
        if action:
            try:
                parsed_action = UIDAction(action)
            except ValueError:
                valid_actions = [e.value for e in UIDAction]
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid action. Valid actions: {valid_actions}"
                )
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        
        audit_data = service.get_audit_trail(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            uid=uid,
            action=parsed_action,
            scanner_id=scanner_id,
            order_id=order_id,
            limit=limit
        )
        
        return envelope(audit_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit trail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit trail: {str(e)}")


@router.get("/ledger/statistics", response_model=dict)
async def get_ledger_statistics(
    days: int = 30,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get UID ledger statistics for dashboard"""
    try:
        from ..services.uid_ledger_service import UIDLedgerService
        
        service = UIDLedgerService(db)
        stats = service.get_statistics(days)
        
        return envelope(stats)
        
    except Exception as e:
        logger.error(f"Error fetching ledger statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ledger statistics: {str(e)}")


@router.post("/uid/{uid}/scan", response_model=dict)
async def record_uid_scan(
    uid: str,
    request: dict,
    db: Session = Depends(get_session),
    current_user = Depends(require_roles(Role.ADMIN))
):
    """Record a new UID scan in the ledger"""
    try:
        from ..services.uid_ledger_service import UIDLedgerService
        from ..models.uid_ledger import UIDAction, LedgerEntrySource
        
        service = UIDLedgerService(db)
        
        # Parse and validate action
        action_str = request.get('action')
        if not action_str:
            raise HTTPException(status_code=400, detail="Action is required")
        
        try:
            action = UIDAction(action_str)
        except ValueError:
            valid_actions = [e.value for e in UIDAction]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Valid actions: {valid_actions}"
            )
        
        # Parse source
        source_str = request.get('source', 'ADMIN_MANUAL')
        try:
            source = LedgerEntrySource(source_str)
        except ValueError:
            valid_sources = [e.value for e in LedgerEntrySource]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Valid sources: {valid_sources}"
            )
        
        # Record the scan
        entry = service.record_scan(
            uid=uid,
            action=action,
            recorded_by=current_user.id,
            scanned_by_admin=current_user.id,
            scanner_name=current_user.name,
            order_id=request.get('order_id'),
            sku_id=request.get('sku_id'),
            source=source,
            lorry_id=request.get('lorry_id'),
            location_notes=request.get('location_notes'),
            notes=request.get('notes'),
            customer_name=request.get('customer_name'),
            order_reference=request.get('order_reference')
        )
        
        return envelope({
            "success": True,
            "message": "UID scan recorded successfully",
            "entry_id": entry.id,
            "uid": uid,
            "action": action.value,
            "recorded_at": entry.recorded_at.isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording UID scan for {uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record UID scan: {str(e)}")