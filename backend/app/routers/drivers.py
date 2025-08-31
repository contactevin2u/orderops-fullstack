from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
import datetime as dt

from ..auth.firebase import driver_auth, firebase_auth, _get_app
from ..auth.deps import require_roles
from ..db import get_session
from ..models import Driver, DriverDevice, Trip, Order, TripEvent, Role, Commission
from ..schemas import (
    DeviceRegisterIn,
    DriverOut,
    DriverOrderOut,
    DriverOrderUpdateIn,
    DriverCreateIn,
    CommissionMonthOut,
)
from ..utils.storage import save_pod_image

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
            # Calculate potential commission split for this driver
            order_total = getattr(order, "total", Decimal("0")) or Decimal("0")
            total_commission_rate = Decimal("0.10")  # 10% total commission
            driver_count = len(trip.driver_ids) if hasattr(trip, 'driver_ids') else 1
            commission_per_driver = (order_total * total_commission_rate) / driver_count
            
            driver_role = "secondary" if current_driver_id == trip.driver_id_2 else "primary"
            commission_info = {
                "amount": str(commission_per_driver),
                "status": "pending",
                "scheme": "percentage_split",
                "rate": str(total_commission_rate / driver_count),
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
        "balance": str(getattr(order, "balance", Decimal("0")) or Decimal("0")),
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
    driver = Driver(firebase_uid=fb_user.uid, name=payload.name, phone=payload.phone)
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver

@router.post("", response_model=DriverOut, dependencies=[Depends(require_roles(Role.ADMIN))])
def create_driver(payload: DriverCreateIn, db: Session = Depends(get_session)):
    try:
        fb_user = firebase_auth.create_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.name,
            app=_get_app(),
        )
    except Exception as exc:  # pragma: no cover - network/cred failures
        raise HTTPException(400, "Failed to create driver") from exc
    driver = Driver(firebase_uid=fb_user.uid, name=payload.name, phone=payload.phone)
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
def list_assigned_orders(driver=Depends(driver_auth), db: Session = Depends(get_session)):
    rows = db.execute(
        select(Trip, Order).join(Order, Trip.order_id == Order.id).where(Trip.driver_id == driver.id)
    ).all()
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
        pass
    db.add(TripEvent(trip_id=trip.id, status=payload.status))
    order = db.get(Order, order_id)
    db.commit()
    return _order_to_driver_out(order, trip.status, trip, driver.id)


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
        select(month_expr.label("month"), func.sum(Commission.computed_amount).label("total"))
        .where(Commission.driver_id == driver.id)
        .group_by("month")
        .order_by("month")
    )
    rows = db.execute(stmt).all()
    return [
        {"month": row.month, "total": float(row.total or 0)}
        for row in rows
    ]


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
