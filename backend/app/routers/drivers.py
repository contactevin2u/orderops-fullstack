from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
import datetime as dt

from ..auth.firebase import driver_auth, firebase_auth, _get_app
from ..auth.deps import require_roles
from ..db import get_session
from ..models import Driver, DriverDevice, Trip, Order, TripEvent, Role, Commission, Customer, UpsellRecord, LorryStock, SKU, OrderItemUID, Item
from ..schemas import (
    DeviceRegisterIn,
    DriverOut,
    DriverOrderOut,
    DriverOrderUpdateIn,
    DriverCreateIn,
    CommissionMonthOut,
    UIDActionIn,
)
from ..utils.storage import save_pod_image
from ..reports.outstanding import compute_balance
from ..core.config import settings
from ..utils.responses import envelope
from ..utils.audit import log_action

router = APIRouter(prefix="/drivers", tags=["drivers"])

def _order_to_driver_out(order: Order, status: str, trip: Trip = None, current_driver_id: int = None) -> dict:
    # delivery_date may be datetime or date
    dd = None
    if getattr(order, "delivery_date", None):
        dd = (
            order.delivery_date.date()
            if hasattr(order.delivery_date, "date")
            else order.delivery_date
        )

    items = []
    try:
        for it in getattr(order, "items", []) or []:
            items.append(
                {
                    "id": it.id,
                    "name": it.name,
                    "qty": it.qty,
                    "unit_price": getattr(it, "unit_price", None),
                    "line_total": getattr(it, "line_total", None),
                    "item_type": getattr(it, "item_type", None),
                }
            )
    except Exception:
        items = []

    try:
        cust = getattr(order, "customer", None)
    except Exception:
        cust = None
    customer = None
    if cust:
        customer = {
            "id": cust.id,
            "name": getattr(cust, "name", None),
            "phone": getattr(cust, "phone", None),
            "address": getattr(cust, "address", None),
            "map_url": getattr(cust, "map_url", None),
        }

    # Calculate commission information for the specific driver
    commission_info = None
    if trip and status.lower() == "delivered" and current_driver_id:
        # Find commission record for this specific driver
        driver_commission = None
        for comm in getattr(trip, "commissions", []):
            if comm.driver_id == current_driver_id:
                driver_commission = comm
                break
        
        if driver_commission:
            # Show actual commission for this driver
            driver_role = "secondary" if current_driver_id == trip.driver_id_2 else "primary"
            commission_info = {
                "amount": str(driver_commission.computed_amount),
                "status": "actualized" if driver_commission.actualized_at else "pending",
                "scheme": driver_commission.scheme,
                "rate": str(driver_commission.rate),
                "role": driver_role
            }
        else:
            # Calculate flat rate commission: RM30 total, split among drivers
            total_commission = Decimal("30.00")  # RM30 flat rate
            driver_count = 2 if trip.driver_id_2 else 1
            commission_per_driver = total_commission / driver_count  # RM30 single or RM15 each
            
            driver_role = "secondary" if current_driver_id == trip.driver_id_2 else "primary"
            commission_info = {
                "amount": str(commission_per_driver),
                "status": "pending",
                "scheme": "flat_rate",
                "rate": str(commission_per_driver),
                "role": driver_role
            }

    return {
        "id": str(order.id),
        "code": getattr(order, "code", None),
        "status": status,
        "customer_name": customer.get("name") if customer else None,
        "customer_phone": customer.get("phone") if customer else None,
        "address": customer.get("address") if customer else None,
        "delivery_date": str(dd) if dd else None,
        "notes": getattr(order, "notes", None),
        "total": str(getattr(order, "total", Decimal("0")) or Decimal("0")),
        "paid_amount": str(getattr(order, "paid_amount", Decimal("0")) or Decimal("0")),
        "balance": str(compute_balance(order, date.today())),
        "type": getattr(order, "type", None),
        "items": items,
        "commission": commission_info,
    }


@router.get("", response_model=list[DriverOut])
def list_drivers(db: Session = Depends(get_session)):
    return db.query(Driver).filter(Driver.is_active == True).limit(1000).all()


@router.post("/register", response_model=DriverOut)
def register_driver_for_testing(payload: DriverCreateIn, db: Session = Depends(get_session)):
    """Register a new driver (testing endpoint - no admin required)"""
    try:
        fb_user = firebase_auth.create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.name,
            app=_get_app(),
        )
    except Exception as exc:  # pragma: no cover - network/cred failures
        raise HTTPException(400, "Failed to create driver") from exc
    driver = Driver(
        firebase_uid=fb_user.uid, 
        name=payload.name, 
        phone=payload.phone,
        base_warehouse=payload.base_warehouse
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver

@router.post("", response_model=DriverOut, dependencies=[Depends(require_roles(Role.ADMIN))])
def create_driver(payload: DriverCreateIn, db: Session = Depends(get_session)):
    # If firebase_uid is provided, use it instead of creating a new Firebase user
    if payload.firebase_uid:
        firebase_uid = payload.firebase_uid
    else:
        # Create new Firebase user
        try:
            fb_user = firebase_auth.create_user(
                email=payload.email,
                password=payload.password,
                display_name=payload.name,
                app=_get_app(),
            )
            firebase_uid = fb_user.uid
        except Exception as exc:  # pragma: no cover - network/cred failures
            raise HTTPException(400, "Failed to create Firebase user") from exc
    
    driver = Driver(
        firebase_uid=firebase_uid, 
        name=payload.name, 
        phone=payload.phone,
        base_warehouse=payload.base_warehouse
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/jobs")
def get_driver_jobs(
    status_filter: str = "active",  # active|completed|all
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Get jobs assigned to the current driver"""
    # Query orders through trips (Order -> Trip -> Driver relationship)
    query = (
        db.query(Order)
        .join(Trip, Order.id == Trip.order_id)
        .filter(Trip.driver_id == driver.id)
        .options(joinedload(Order.customer))
    )
    
    if status_filter == "active":
        # Active trips: ASSIGNED, IN_TRANSIT, ON_HOLD (not yet delivered)
        query = query.filter(Trip.status.in_(["ASSIGNED", "IN_TRANSIT", "ON_HOLD"]))
        print(f"DEBUG: Filtering active jobs for driver {driver.id} - looking for trip statuses: ASSIGNED, IN_TRANSIT, ON_HOLD")
    elif status_filter == "completed":
        # Completed trips: DELIVERED or cancelled/returned orders
        query = query.filter(
            (Trip.status == "DELIVERED") |
            (Order.status.in_(["COMPLETED", "RETURNED", "CANCELLED"]))
        )
        print(f"DEBUG: Filtering completed jobs for driver {driver.id} - looking for trip status DELIVERED or order status COMPLETED/RETURNED/CANCELLED")
    # if "all", no additional filtering
    
    orders = query.order_by(Order.delivery_date.desc().nullslast(), Order.created_at.desc()).all()
    
    print(f"DEBUG: Found {len(orders)} orders with status_filter='{status_filter}' for driver {driver.id}")
    
    # Get trips for proper status
    trips_dict = {}
    for order in orders:
        trip = db.query(Trip).filter(Trip.order_id == order.id, Trip.driver_id == driver.id).first()
        if trip:
            trips_dict[order.id] = trip
            print(f"DEBUG: Order {order.id} - Order status: {order.status}, Trip status: {trip.status}")
    
    return [
        _order_to_driver_out(
            order, 
            trips_dict.get(order.id).status.lower() if trips_dict.get(order.id) else order.status.lower(), 
            trips_dict.get(order.id),
            driver.id
        )
        for order in orders
    ]

@router.get("/jobs/{job_id}")
def get_driver_job(
    job_id: str,  # Keep as str for URL parameter
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Get specific job details for the driver"""
    try:
        order_id_int = int(job_id)  # Convert string to int
    except ValueError:
        raise HTTPException(400, "Invalid job ID")
        
    order = (
        db.query(Order)
        .join(Trip, Order.id == Trip.order_id)
        .filter(
            Order.id == order_id_int,  # Use converted int
            Trip.driver_id == driver.id
        )
        .options(joinedload(Order.customer))
        .first()
    )
    
    if not order:
        raise HTTPException(404, "Job not found")
    
    # Get trip for proper status
    trip = db.query(Trip).filter(Trip.order_id == order.id, Trip.driver_id == driver.id).first()
    trip_status = trip.status.lower() if trip else order.status.lower()
    
    return _order_to_driver_out(order, trip_status, trip, driver.id)

@router.post("/locations")
def post_driver_locations(
    locations: list,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Receive location updates from driver app"""
    # For now, just return success
    # You can implement location storage here if needed
    return {"status": "ok", "count": len(locations)}

@router.post("/devices")
def register_device(
    payload: DeviceRegisterIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    device = (
        db.query(DriverDevice)
        .filter(
            DriverDevice.driver_id == driver.id,
            DriverDevice.token == payload.token,
        )
        .one_or_none()
    )
    if device:
        device.driver_id = driver.id
        device.platform = payload.platform
        device.app_version = payload.app_version
        device.model = payload.model
    else:
        device = DriverDevice(
            driver_id=driver.id,
            token=payload.token,
            platform=payload.platform,
            app_version=payload.app_version,
            model=payload.model,
        )
        db.add(device)
    db.commit()
    return {"status": "ok"}


@router.get("/orders", response_model=list[DriverOrderOut])
def list_assigned_orders(
    month: str | None = None,  # YYYY-MM format
    driver=Depends(driver_auth), 
    db: Session = Depends(get_session)
):
    """List orders assigned to driver, optionally filtered by month"""
    query = (
        select(Trip, Order)
        .join(Order, Trip.order_id == Order.id)
        .where(Trip.driver_id == driver.id)
    )
    
    # Add month filter if provided
    if month:
        try:
            year, month_num = map(int, month.split('-'))
            # Filter by delivery_date within the specified month
            from sqlalchemy import extract, and_
            query = query.where(and_(
                extract('year', Order.delivery_date) == year,
                extract('month', Order.delivery_date) == month_num
            ))
        except (ValueError, AttributeError):
            # Invalid month format, ignore filter
            pass
    
    rows = db.execute(query).all()
    out = []
    for trip, order in rows:
        out.append(_order_to_driver_out(order, trip.status, trip, driver.id))
    return out


@router.get("/orders/{order_id}", response_model=DriverOrderOut)
def get_assigned_order(order_id: int, driver=Depends(driver_auth), db: Session = Depends(get_session)):
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_driver_out(order, trip.status, trip, driver.id)


@router.post("/orders/{order_id}/pod-photo", response_model=dict)
def upload_pod_photo(
    order_id: int,
    file: UploadFile = File(...),
    photo_number: int = 1,  # Which photo slot (1, 2, or 3)
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(404, "Trip not found")
    
    if photo_number not in [1, 2, 3]:
        raise HTTPException(400, "Photo number must be 1, 2, or 3")
        
    data = file.file.read()
    try:
        url = save_pod_image(data)
    except Exception as e:  # pragma: no cover - pillow errors
        raise HTTPException(400, str(e)) from e
    
    # Store in the appropriate photo slot
    if photo_number == 1:
        trip.pod_photo_url_1 = url
    elif photo_number == 2:
        trip.pod_photo_url_2 = url
    elif photo_number == 3:
        trip.pod_photo_url_3 = url
    
    # Also update the legacy field for backward compatibility
    if photo_number == 1:
        trip.pod_photo_url = url
        
    db.commit()
    db.refresh(trip)
    return {"url": url, "photo_number": photo_number}


def _process_uid_actions(
    order_id: int, 
    uid_actions: list[UIDActionIn], 
    driver_id: int, 
    db: Session
) -> tuple[int, list[str]]:
    """
    Process UID actions during order completion - UNIFIED INVENTORY SYSTEM
    Returns (success_count, error_messages).
    Syncs both legacy and lorry inventory systems.
    """
    if not settings.UID_INVENTORY_ENABLED:
        return 0, ["UID inventory system disabled"]
    
    success_count = 0
    errors = []
    
    try:
        # Initialize unified inventory service
        from ..services.lorry_inventory_service import LorryInventoryService
        lorry_service = LorryInventoryService(db)
        
        # Get driver's lorry assignment
        assignment = db.execute(
            select(LorryAssignment).where(
                and_(
                    LorryAssignment.driver_id == driver_id,
                    LorryAssignment.assignment_date <= date.today()
                )
            ).order_by(LorryAssignment.assignment_date.desc()).limit(1)
        ).scalar_one_or_none()
        
        lorry_id = assignment.lorry_id if assignment else f"DRIVER_{driver_id}"
        print(f"DEBUG: Processing UID actions for lorry {lorry_id}")
        
        # Convert to lorry action format
        lorry_actions = []
        for uid_action in uid_actions:
            lorry_actions.append({
                "action": uid_action.action.upper(),  # Ensure uppercase
                "uid": uid_action.uid,
                "notes": uid_action.notes or f"Order {order_id} completion"
            })
        
        # Process through unified lorry system
        lorry_result = lorry_service.process_delivery_actions(
            lorry_id=lorry_id,
            order_id=order_id,
            driver_id=driver_id,
            admin_user_id=driver_id,  # Driver as admin for their actions
            uid_actions=lorry_actions
        )
        
        if lorry_result.get("success", False):
            success_count = lorry_result.get("processed_count", 0)
            print(f"DEBUG: Lorry system processed {success_count} UID actions successfully")
            
            # Also process legacy system for backward compatibility
            for uid_action in uid_actions:
                try:
                    # Check for duplicate scans (idempotent)
                    existing = db.execute(
                        select(OrderItemUID).where(
                            and_(
                                OrderItemUID.order_id == order_id,
                                OrderItemUID.uid == uid_action.uid,
                                OrderItemUID.action == uid_action.action
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if not existing:
                        # Create legacy scan record for compatibility
                        scan_record = OrderItemUID(
                            order_id=order_id,
                            uid=uid_action.uid,
                            scanned_by=driver_id,
                            action=uid_action.action,
                            scanned_at=datetime.now(timezone.utc),
                            notes=uid_action.notes
                        )
                        db.add(scan_record)
                        
                except Exception as e:
                    print(f"DEBUG: Legacy system sync warning for UID {uid_action.uid}: {e}")
                    # Don't fail for legacy sync issues
            
            # Log audit action
            log_action(
                db, 
                user_id=driver_id, 
                action="UID_UNIFIED_SCAN", 
                resource_type="order", 
                resource_id=order_id,
                details={
                    "uid_actions": [{"action": ua.action, "uid": ua.uid} for ua in uid_actions],
                    "success_count": success_count,
                    "lorry_id": lorry_id,
                    "system": "unified_inventory"
                }
            )
            
        else:
            # Fallback to legacy system if lorry system fails
            print(f"DEBUG: Lorry system failed, falling back to legacy: {lorry_result.get('message', 'Unknown error')}")
            errors.extend(lorry_result.get("errors", []))
            
            # Process with legacy system
            for uid_action in uid_actions:
                try:
                    # Validate UID exists
                    item = db.get(Item, uid_action.uid)
                    if not item:
                        errors.append(f"UID {uid_action.uid} not found in inventory")
                        continue
                    
                    # Check for duplicate scans (idempotent)
                    existing = db.execute(
                        select(OrderItemUID).where(
                            and_(
                                OrderItemUID.order_id == order_id,
                                OrderItemUID.uid == uid_action.uid,
                                OrderItemUID.action == uid_action.action
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing:
                        # Already processed - idempotent behavior
                        success_count += 1
                        continue
                    
                    # Create scan record
                    scan_record = OrderItemUID(
                        order_id=order_id,
                        uid=uid_action.uid,
                        scanned_by=driver_id,
                        action=uid_action.action,
                        scanned_at=datetime.now(timezone.utc),
                        notes=uid_action.notes
                    )
                    db.add(scan_record)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to process UID {uid_action.uid}: {str(e)}")
        
        # Commit all changes
        if success_count > 0:
            db.commit()
            print(f"DEBUG: Successfully committed {success_count} UID actions to unified system")
        
    except Exception as e:
        print(f"DEBUG: UID processing error: {e}")
        errors.append(f"UID processing system error: {str(e)}")
        db.rollback()
        success_count = 0
    
    return success_count, errors


@router.patch("/orders/{order_id}", response_model=DriverOrderOut)  
def update_order_status(
    order_id: int,
    payload: DriverOrderUpdateIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    # Debug logging
    print(f"DEBUG: Driver {driver.id} attempting to update order {order_id} to status '{payload.status}'")
    
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        print(f"DEBUG: Trip not found for order {order_id}, driver {driver.id}")
        raise HTTPException(404, "Trip not found")
    
    print(f"DEBUG: Current trip status: {trip.status}")
    
    if payload.status not in {"IN_TRANSIT", "DELIVERED", "ON_HOLD"}:
        print(f"DEBUG: Invalid status received: '{payload.status}'")
        raise HTTPException(400, f"Invalid status: '{payload.status}'. Must be one of: IN_TRANSIT, DELIVERED, ON_HOLD")
    
    # Business rule: Only one trip can be IN_TRANSIT at a time per driver
    if payload.status == "IN_TRANSIT":
        active_trip = db.query(Trip).filter(
            Trip.driver_id == driver.id,
            Trip.status == "IN_TRANSIT",
            Trip.id != trip.id  # Exclude current trip
        ).first()
        
        if active_trip:
            # Get order details for better error message
            active_order = db.get(Order, active_trip.order_id)
            order_info = f"Order #{active_order.code}" if active_order and active_order.code else f"Order ID {active_trip.order_id}"
            print(f"DEBUG: Blocking IN_TRANSIT - driver {driver.id} has active trip {active_trip.id} for {order_info}")
            raise HTTPException(
                400, 
                f"You already have an order in transit ({order_info}). Please put it on hold or complete it first."
            )
    

    trip.status = payload.status
    now = datetime.now(timezone.utc)
    if payload.status == "IN_TRANSIT":
        if not trip.started_at:
            trip.started_at = now
    elif payload.status == "DELIVERED":
        pod_urls = trip.pod_photo_urls
        print(f"DEBUG: Checking PoD photos for DELIVERED status. Found {len(pod_urls)} photos: {pod_urls}")
        if not trip.has_pod_photos:
            print(f"DEBUG: Blocking DELIVERED status - PoD photos required but not found")
            raise HTTPException(400, "At least one Proof of Delivery photo is required before marking order as delivered. Please take photos of the delivered items first.")
        trip.delivered_at = now
    elif payload.status == "ON_HOLD":
        # Driver pausing their own delivery - keep assignment but change status
        print(f"DEBUG: ON_HOLD - Driver {driver.id} pausing their own delivery for trip {trip.id}")
        # Keep driver_id and route_id - this is just a temporary pause by the same driver
        pass
    
    db.add(TripEvent(trip_id=trip.id, status=payload.status))
    
    # Process UID actions if provided (new integrated feature)
    uid_success_count = 0
    uid_errors = []
    if payload.uid_actions:
        print(f"DEBUG: Processing {len(payload.uid_actions)} UID actions for order {order_id}")
        uid_success_count, uid_errors = _process_uid_actions(order_id, payload.uid_actions, driver.id, db)
        
        if uid_errors:
            print(f"DEBUG: UID processing errors: {uid_errors}")
            # Continue with order completion even if some UIDs failed
            # This maintains backward compatibility
        
        if uid_success_count > 0:
            print(f"DEBUG: Successfully processed {uid_success_count} UID actions")
    
    order = db.get(Order, order_id)
    db.commit()
    
    # Return enhanced response with UID info if processed
    response = _order_to_driver_out(order, trip.status, trip, driver.id)
    if payload.uid_actions:
        # Add UID processing results to response (non-breaking addition)
        response["uid_processing"] = {
            "success_count": uid_success_count,
            "total_requested": len(payload.uid_actions),
            "errors": uid_errors
        }
    
    return response


@router.get("/commissions", response_model=list[CommissionMonthOut])
def my_commissions(
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    month_expr = (
        func.strftime("%Y-%m", Commission.created_at)
        if db.bind.dialect.name == "sqlite"
        else func.to_char(Commission.created_at, "YYYY-MM")
    )
    stmt = (
        select(
            month_expr.label("month"), 
            func.sum(Commission.computed_amount).label("total"),
            func.count(Commission.id).label("commission_count")
        )
        .where(
            and_(
                Commission.driver_id == driver.id,
                Commission.actualized_at.isnot(None)  # Only count released commissions
            )
        )
        .group_by("month")
        .order_by("month")
    )
    rows = db.execute(stmt).all()
    return [
        {"month": row.month, "total": float(row.total or 0)}
        for row in rows
    ]


@router.get("/commissions/detailed", response_model=dict)
def my_detailed_commissions(
    month: str | None = None,  # Format: YYYY-MM
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Get detailed commission info with orders for a specific month"""
    
    # Default to current month if not specified
    if not month:
        current_date = dt.datetime.now()
        month = f"{current_date.year}-{current_date.month:02d}"
    
    # Query commissions with order details for the specified month
    month_expr = (
        func.strftime("%Y-%m", Commission.created_at)
        if db.bind.dialect.name == "sqlite"
        else func.to_char(Commission.created_at, "YYYY-MM")
    )
    
    commissions = (
        db.query(Commission)
        .join(Trip)
        .join(Order)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(
            and_(
                Commission.driver_id == driver.id,
                Commission.actualized_at.isnot(None),  # Only released commissions
                month_expr == month
            )
        )
        .options(
            joinedload(Commission.trip).joinedload(Trip.order).joinedload(Order.customer)
        )
        .all()
    )
    
    # Group by order and calculate totals
    orders_data = []
    total_released = 0
    
    for commission in commissions:
        trip = commission.trip
        order = trip.order
        
        # Check if this is a secondary driver (commission split scenario)
        is_secondary = trip.driver_id_2 and commission.driver_id == trip.driver_id_2
        
        orders_data.append({
            "order_id": order.id,
            "order_code": order.code,
            "customer_name": order.customer.name,
            "commission_amount": float(commission.computed_amount),
            "driver_role": "secondary" if is_secondary else "primary",
            "has_secondary_driver": bool(trip.driver_id_2),
            "released_at": commission.actualized_at.isoformat() if commission.actualized_at else None,
            "order_total": float(order.total)
        })
        
        total_released += float(commission.computed_amount)
    
    return {
        "month": month,
        "total_released": total_released,
        "orders_count": len(orders_data),
        "orders": orders_data
    }


@router.get("/upsell-incentives", response_model=dict)
def my_upsell_incentives(
    month: str | None = None,  # Format: YYYY-MM
    status: str | None = None,  # PENDING, RELEASED
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    """Get driver's upsell incentives"""
    
    query = (
        db.query(UpsellRecord)
        .filter(UpsellRecord.driver_id == driver.id)
        .options(joinedload(UpsellRecord.order))
        .order_by(UpsellRecord.created_at.desc())
    )
    
    # Filter by month if provided
    if month:
        month_expr = (
            func.strftime("%Y-%m", UpsellRecord.created_at)
            if db.bind.dialect.name == "sqlite"
            else func.to_char(UpsellRecord.created_at, "YYYY-MM")
        )
        query = query.filter(month_expr == month)
    
    # Filter by status if provided  
    if status:
        query = query.filter(UpsellRecord.incentive_status == status.upper())
    
    upsell_records = query.all()
    
    # Format response
    incentives = []
    total_pending = 0
    total_released = 0
    
    for record in upsell_records:
        import json
        items_data = json.loads(record.items_data) if record.items_data else []
        
        incentive_data = {
            "id": record.id,
            "order_id": record.order_id,
            "order_code": record.order.code,
            "upsell_amount": float(record.upsell_amount),
            "driver_incentive": float(record.driver_incentive),
            "status": record.incentive_status,
            "items_upsold": items_data,
            "notes": record.upsell_notes,
            "created_at": record.created_at.isoformat(),
            "released_at": record.released_at.isoformat() if record.released_at else None
        }
        incentives.append(incentive_data)
        
        if record.incentive_status == "PENDING":
            total_pending += float(record.driver_incentive)
        elif record.incentive_status == "RELEASED":
            total_released += float(record.driver_incentive)
    
    return {
        "incentives": incentives,
        "summary": {
            "total_pending": total_pending,
            "total_released": total_released,
            "total_records": len(incentives)
        }
    }


@router.get("/{driver_id}", response_model=DriverOut, dependencies=[Depends(require_roles(Role.ADMIN))])
def get_driver(driver_id: int, db: Session = Depends(get_session)):
    """Get a single driver by ID"""
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404, "Driver not found")
    return driver


@router.put("/{driver_id}", response_model=DriverOut, dependencies=[Depends(require_roles(Role.ADMIN))])
def update_driver(driver_id: int, payload: dict, db: Session = Depends(get_session)):
    """Update driver details"""
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404, "Driver not found")
    
    # Update allowed fields
    allowed_fields = {"name", "phone", "base_warehouse"}
    for field, value in payload.items():
        if field in allowed_fields and hasattr(driver, field):
            setattr(driver, field, value)
    
    db.commit()
    return driver


@router.get(
    "/{driver_id}/commissions",
    response_model=list[CommissionMonthOut],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def driver_commissions(driver_id: int, db: Session = Depends(get_session)):
    month_expr = (
        func.strftime("%Y-%m", Commission.created_at)
        if db.bind.dialect.name == "sqlite"
        else func.to_char(Commission.created_at, "YYYY-MM")
    )
    stmt = (
        select(month_expr.label("month"), func.sum(Commission.computed_amount).label("total"))
        .where(Commission.driver_id == driver_id)
        .group_by("month")
        .order_by("month")
    )
    rows = db.execute(stmt).all()
    return [
        {"month": row.month, "total": float(row.total or 0)}
        for row in rows
    ]


@router.get("/{driver_id}/lorry-stock/{date}", response_model=dict)
def get_lorry_stock(
    driver_id: int,
    date: str,  # YYYY-MM-DD format
    db: Session = Depends(get_session),
    current_user=Depends(require_roles(Role.ADMIN, Role.CASHIER))
):
    """Get lorry stock for driver on specific date - integrates with enhanced UID inventory system"""
    if not settings.UID_INVENTORY_ENABLED:
        return envelope({
            "date": date,
            "driver_id": driver_id,
            "items": [],
            "total_expected": 0,
            "total_scanned": 0,
            "total_variance": 0
        })
    
    try:
        # Parse date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get stock records with SKU details
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
    
    items = []
    total_expected = 0
    total_scanned = 0
    total_variance = 0
    
    for stock, sku in stock_records:
        # For compatibility, map the enhanced backend format to driver app format
        # In the enhanced system, we calculate expected vs counted
        expected_count = 0  # Would be calculated from previous day + transactions
        scanned_count = stock.qty_counted
        variance = scanned_count - expected_count
        
        items.append({
            "sku_id": sku.id,
            "sku_name": sku.name,
            "expected_count": expected_count,
            "scanned_count": scanned_count,
            "variance": variance
        })
        
        total_expected += expected_count
        total_scanned += scanned_count
        total_variance += variance
    
    response_data = {
        "date": date,
        "driver_id": driver_id,
        "items": items,
        "total_expected": total_expected,
        "total_scanned": total_scanned,
        "total_variance": total_variance
    }
    
    print(f"DEBUG: Returning lorry stock response: {response_data}")
    return envelope(response_data)