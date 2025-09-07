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
from ..models import Order, OrderItemUID, Item, SKU, LorryStock, SKUAlias, Driver
from ..models.item import ItemType, ItemStatus
from ..models.order_item_uid import UIDAction
from ..services.inventory_service import InventoryService
from ..auth.deps import require_roles, Role, get_current_user
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
    
    # Validate each UID
    for uid in request.uids:
        # Check if UID exists
        item = db.get(Item, uid)
        if not item:
            errors.append(f"UID {uid} not found in inventory")
            continue
        
        # Check if already scanned for this order (idempotent)
        existing = db.execute(
            select(OrderItemUID).where(
                and_(
                    OrderItemUID.order_id == order_id,
                    OrderItemUID.uid == uid,
                    OrderItemUID.action == "ISSUE"
                )
            )
        ).scalar_one_or_none()
        
        if existing:
            # Idempotent - already scanned
            scanned_count += 1
            continue
        
        # Create new scan record
        try:
            scan_record = OrderItemUID(
                order_id=order_id,
                uid=uid,
                scanned_by=request.driver_id,
                action="ISSUE",
                scanned_at=datetime.utcnow()
            )
            db.add(scan_record)
            scanned_count += 1
        except Exception as e:
            errors.append(f"Failed to record UID {uid}: {str(e)}")
    
    try:
        db.commit()
        
        # Log audit action
        log_action(
            db, 
            user_id=request.driver_id, 
            action="UID_SCAN_ISSUE", 
            resource_type="order", 
            resource_id=order_id,
            details={"uids": request.uids, "scanned_count": scanned_count}
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
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
    
    for uid in request.uids:
        item = db.get(Item, uid)
        if not item:
            errors.append(f"UID {uid} not found in inventory")
            continue
        
        # Check if already returned (idempotent)
        existing = db.execute(
            select(OrderItemUID).where(
                and_(
                    OrderItemUID.order_id == order_id,
                    OrderItemUID.uid == uid,
                    OrderItemUID.action == "RETURN"
                )
            )
        ).scalar_one_or_none()
        
        if existing:
            scanned_count += 1
            continue
        
        try:
            scan_record = OrderItemUID(
                order_id=order_id,
                uid=uid,
                scanned_by=request.driver_id,
                action="RETURN",
                scanned_at=datetime.utcnow()
            )
            db.add(scan_record)
            scanned_count += 1
        except Exception as e:
            errors.append(f"Failed to record UID {uid}: {str(e)}")
    
    try:
        db.commit()
        log_action(
            db, 
            user_id=request.driver_id, 
            action="UID_SCAN_RETURN", 
            resource_type="order", 
            resource_id=order_id,
            details={"uids": request.uids, "scanned_count": scanned_count}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
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
async def get_lorry_stock(
    driver_id: int,
    date: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user = Depends(driver_auth)
):
    """Get lorry stock snapshot for a specific date"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"message": "UID inventory system disabled", "lines": []})
    
    # Parse date or use today
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.utcnow().date()
    
    # Get stock records
    stock_records = db.execute(
        select(LorryStock, SKU)
        .join(SKU, LorryStock.sku_id == SKU.id)
        .where(
            and_(
                LorryStock.driver_id == driver_id,
                LorryStock.as_of_date == target_date
            )
        )
        .order_by(SKU.code)
    ).all()
    
    lines = []
    for stock, sku in stock_records:
        lines.append({
            "sku_id": sku.id,
            "sku_code": sku.code,
            "sku_name": sku.name,
            "qty_counted": stock.qty_counted,
            "uploaded_at": stock.uploaded_at.isoformat(),
            "uploaded_by": stock.uploaded_by
        })
    
    return envelope({"date": target_date.isoformat(), "lines": lines})


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
async def get_inventory_config(
    current_user = Depends(get_current_user)
):
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
    """Enhanced UID scanning with extended actions"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({"success": True, "message": "UID inventory disabled"})
    
    try:
        service = InventoryService(db)
        
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
            notes=request.notes
        )
        
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


@router.get("/orders/{order_id}/uids", response_model=dict)
async def get_order_uids(
    order_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get all UID scans for an order - integrates with commission checking"""
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


@router.post("/sku/resolve", response_model=dict)
async def resolve_sku(
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


@router.post("/sku/alias", response_model=dict)
async def add_sku_alias(
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
async def get_driver_stock_status(
    driver_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get current items with driver - for load-out/load-in workflow"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({
            "driver_id": driver_id,
            "stock_items": [],
            "total_items": 0
        })
    
    try:
        service = InventoryService(db)
        result = service.get_driver_stock_status(driver_id)
        return envelope(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lorry-stock/upload", response_model=dict)
async def upload_lorry_stock(
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