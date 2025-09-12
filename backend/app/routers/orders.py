from fastapi import APIRouter, Depends, HTTPException, Query, Header, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, date as date_cls, time, timedelta, timezone
from zoneinfo import ZoneInfo

from ..db import get_session
from ..models import (
    Order,
    OrderItem,
    Plan,
    Customer,
    IdempotentRequest,
    Role,
    User,
    Driver,
    Trip,
    Commission,
)
from ..auth.deps import require_roles
from ..auth.firebase import driver_auth
from ..utils.audit import log_action
from ..schemas import OrderOut, AssignDriverIn, AssignSecondDriverIn
from ..services.ordersvc import (
    create_order_from_parsed,
    recompute_financials,
    _sum_posted_payments,
    q2,
    ensure_plan_first_month_fee,
)
from ..reports.outstanding import compute_expected_for_order, calculate_plan_due, compute_balance
from ..services.status_updates import (
    apply_buyback,
    cancel_installment,
    mark_cancelled,
    mark_returned,
)
from ..services.documents import invoice_pdf, quotation_pdf
from ..utils.responses import envelope
from ..utils.normalize import to_decimal
from ..services.fcm import notify_order_assigned

APP_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def kl_day_bounds(d: datetime | date_cls):
    """Return (start_utc, end_utc) for KL local day covering date d."""
    if isinstance(d, datetime):
        d = d.date()
    start_local = datetime.combine(d, time.min, tzinfo=APP_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def trigger_auto_assignment(db: Session, order_id: int):
    """Trigger auto-assignment after order creation"""
    try:
        from ..services.assignment_service import AssignmentService
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Triggering auto-assignment after order {order_id} creation")
        
        # Use the existing database session but ensure it's in a good state
        # The session should be committed by now, so we can use it for queries
        try:
            service = AssignmentService(db)
            result = service.auto_assign_all()
            
            logger.info(f"Auto-assignment result for order {order_id}: {result.get('message', 'Unknown result')}")
            print(f"Auto-assignment triggered after order {order_id} creation: {result.get('message', 'Unknown result')}")
            return result
            
        except Exception as session_error:
            # If there's a session issue, try with a fresh session
            logger.warning(f"Session issue, trying fresh session: {session_error}")
            from ..db import get_session
            
            for fresh_db in get_session():
                service = AssignmentService(fresh_db)
                result = service.auto_assign_all()
                
                logger.info(f"Auto-assignment result (fresh session) for order {order_id}: {result.get('message', 'Unknown result')}")
                print(f"Auto-assignment triggered (fresh session) after order {order_id} creation: {result.get('message', 'Unknown result')}")
                return result
            
    except Exception as e:
        import logging
        import traceback
        
        logger = logging.getLogger(__name__)
        logger.error(f"Auto-assignment failed after order {order_id} creation: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"Auto-assignment failed after order {order_id} creation: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        # Don't fail order creation if assignment fails
        return None


def kl_month_bounds(year: int, month: int):
    """Return (start_utc, end_utc) for KL local month."""
    start_local = datetime(year, month, 1, tzinfo=APP_TZ)
    end_local = (start_local.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)

class OrderListOut(OrderOut):
    customer_name: str

@router.get("", response_model=dict)
def list_orders(
    q: str | None = None,
    status: str | None = None,
    type: str | None = None,
    date: str | None = None,
    unassigned: bool = False,
    driver_id: int | None = None,
    month: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
):
    stmt = (
        select(
            Order,
            Customer.name.label("customer_name"),
            Customer.address.label("customer_address"),
            Trip,
            Driver.name.label("driver_name"),
            Commission,
        )
        .join(Customer, Customer.id == Order.customer_id)
        .join(Trip, Trip.order_id == Order.id, isouter=True)
        .join(Driver, Driver.id == Trip.driver_id, isouter=True)
        .join(Commission, Commission.trip_id == Trip.id, isouter=True)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Order.code.ilike(like), Customer.name.ilike(like), Customer.phone.ilike(like))
        )
    if status:
        stmt = stmt.where(Order.status == status)
    if type:
        stmt = stmt.where(Order.type == type)

    if driver_id is not None:
        stmt = stmt.where(Trip.driver_id == driver_id)

    if month:
        try:
            y, m = map(int, month.split("-"))
            start_utc, end_utc = kl_month_bounds(y, m)
            stmt = stmt.where(
                and_(Order.delivery_date >= start_utc, Order.delivery_date < end_utc)
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid month format (expected YYYY-MM)")

    # --- Date filtering (backlog semantics) ---
    if date:
        try:
            d = datetime.fromisoformat(date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)")

        start_utc, end_utc = kl_day_bounds(d)

        backlog_mode = (unassigned is True) or (status == "ON_HOLD")

        if backlog_mode:
            stmt = stmt.where(
                or_(
                    Order.delivery_date.is_(None),
                    Order.delivery_date < end_utc,
                )
            )
        else:
            stmt = stmt.where(
                and_(
                    Order.delivery_date >= start_utc,
                    Order.delivery_date < end_utc,
                )
            )

    if unassigned:
        # No trip or trip has no route yet (still not assigned to a route)
        stmt = stmt.where(and_(or_(Trip.id.is_(None), Trip.route_id.is_(None))))
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    out: list[OrderListOut] = []
    for (order, customer_name, customer_address, trip, driver_name, commission) in rows:
        dto = OrderOut.model_validate(order).model_dump()
        # Replace static balance with dynamic outstanding calculation
        dto["balance"] = float(compute_balance(order, date_cls.today()))
        dto["customer_name"] = customer_name
        dto["customer_address"] = customer_address
        if trip:
            trip_dto = {
                "id": trip.id,
                "driver_id": trip.driver_id,
                "status": trip.status,
                "driver_name": driver_name,
                "route_id": trip.route_id,
                "pod_photo_url": trip.pod_photo_url,  # Kept for backward compatibility
                "pod_photo_urls": trip.pod_photo_urls,
            }
            if commission:
                trip_dto["commission"] = {
                    "id": commission.id,
                    "scheme": commission.scheme,
                    "rate": commission.rate,
                    "computed_amount": commission.computed_amount,
                    "actualized_at": commission.actualized_at,
                }
            dto["trip"] = trip_dto
        out.append(OrderListOut.model_validate(dto))
    return envelope(out)

class ManualOrderIn(BaseModel):
    customer: dict
    order: dict


class PlanPatch(BaseModel):
    plan_type: str | None = None
    months: int | None = None
    monthly_amount: float | None = None
    status: str | None = None
    start_date: str | None = None


class OrderItemPatch(BaseModel):
    id: int | None = None
    name: str | None = None
    item_type: str | None = None
    sku: str | None = None
    category: str | None = None
    qty: int | None = None
    unit_price: float | None = None
    line_total: float | None = None


class OrderPatch(BaseModel):
    code: str | None = None
    type: str | None = None
    customer_id: int | None = None
    notes: str | None = None
    status: str | None = None
    delivery_date: str | None = None
    # Settable money fields (fees and charges)
    discount: float | None = None
    delivery_fee: float | None = None
    return_delivery_fee: float | None = None
    penalty_fee: float | None = None
    paid_amount: float | None = None
    # Note: subtotal, total, and balance are calculated automatically
    plan: PlanPatch | None = None
    items: list[OrderItemPatch] | None = None
    delete_items: list[int] | None = None

@router.post("", response_model=dict, status_code=201)
def create_order(
    body: ManualOrderIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    try:
        if idempotency_key:
            existing = db.query(Order).filter_by(idempotency_key=idempotency_key).one_or_none()
            if existing:
                return envelope(OrderOut.model_validate(existing))
        order = create_order_from_parsed(db, {"customer": body.customer, "order": body.order})
        if idempotency_key:
            order.idempotency_key = idempotency_key
        db.commit()
        db.refresh(order)
        log_action(db, current_user, "order.create", f"order_id={order.id}")
        
        # Trigger auto-assignment after order creation (use AssignmentService directly)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"About to trigger auto-assignment for order {order.id}")
        print(f"About to trigger auto-assignment for order {order.id}")
        
        try:
            from ..services.assignment_service import AssignmentService
            assignment_service = AssignmentService(db)
            trigger_result = assignment_service.auto_assign_all()
            logger.info(f"Auto-assignment completed for order {order.id}: {trigger_result}")
            print(f"Auto-assignment completed for order {order.id}: {trigger_result}")
        except Exception as e:
            logger.error(f"Auto-assignment failed for order {order.id}: {e}")
            print(f"Auto-assignment failed for order {order.id}: {e}")
            # Don't fail order creation if assignment fails
            trigger_result = {"success": False, "error": str(e)}
        
        return envelope(OrderOut.model_validate(order))
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "required" in error_msg.lower():
            raise HTTPException(
                status_code=400, 
                detail="Missing required information. Please check that all required fields are filled in."
            )
        elif "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=409, 
                detail="This order already exists. Please check if it was created already."
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unable to create order. Please check your information and try again."
            )

@router.get("/{order_id}", response_model=dict)
def get_order(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Order #{order_id} not found. It may have been deleted or moved."
        )
    return envelope(OrderOut.model_validate(order))


@router.get("/{order_id}/invoice.pdf")
def get_invoice_pdf(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Cannot generate invoice: Order #{order_id} not found."
        )
    try:
        pdf = invoice_pdf(order)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="invoice_{order.code}.pdf"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate invoice PDF. Please try again in a moment."
        )


class QuotationIn(BaseModel):
    customer: dict
    order: dict
    quote_date: str | None = None
    valid_until: str | None = None


@router.post("/quotation.pdf")
def generate_quotation_pdf(body: QuotationIn):
    """Generate a quotation PDF without storing anything."""
    from datetime import datetime, timedelta
    
    # Add current date if not provided
    quote_data = body.model_dump()
    if not quote_data.get("quote_date"):
        quote_data["quote_date"] = datetime.now().strftime("%Y-%m-%d")
    if not quote_data.get("valid_until"):
        valid_date = datetime.now() + timedelta(days=30)
        quote_data["valid_until"] = valid_date.strftime("%Y-%m-%d")
    
    pdf = quotation_pdf(quote_data)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="quotation.pdf"'},
    )


@router.get("/{order_id}/due", response_model=dict)  
# Outstanding calculation - simplified business logic:
# OUTRIGHT: Static balance only | RENTAL: Monthly accrual until returned | INSTALLMENT: Monthly accrual until cancelled
def get_order_due(order_id: int, as_of: date_cls | None = None, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    as_of = as_of or date_cls.today()

    expected = compute_expected_for_order(order, as_of)
    paid = _sum_posted_payments(order) + sum(
        (_sum_posted_payments(ch) for ch in getattr(order, "adjustments", []) or []),
        Decimal("0"),
    )
    balance = q2(expected - paid)
    to_collect = q2(balance if balance > 0 else Decimal("0"))
    to_refund = q2(-balance if balance < 0 else Decimal("0"))
    accrued = calculate_plan_due(order.plan, as_of)

    return envelope(
        {
            "expected": float(expected),
            "paid": float(paid),
            "balance": float(balance),
            "to_collect": float(to_collect),
            "to_refund": float(to_refund),
            "accrued": float(accrued),
        }
    )


@router.patch("/{order_id}", response_model=dict)
def update_order(order_id: int, body: OrderPatch, db: Session = Depends(get_session)):
    print(f"DEBUG: Updating order {order_id} with data: {body.model_dump(exclude_none=True)}")
    
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    data = body.model_dump(exclude_none=True)
    print(f"DEBUG: Processing update data: {data}")

    # Handle order code with uniqueness validation
    if "code" in data:
        new_code = data["code"].strip().upper() if data["code"] else ""
        if new_code and new_code != order.code:
            # Check if code already exists for another order
            existing = db.query(Order).filter(Order.code == new_code, Order.id != order.id).first()
            if existing:
                raise HTTPException(400, f"Order code '{new_code}' already exists")
            order.code = new_code
    
    # Handle order type with validation
    if "type" in data:
        valid_types = ["OUTRIGHT", "INSTALLMENT", "RENTAL", "MIXED"]
        new_type = data["type"].strip().upper() if data["type"] else ""
        if new_type and new_type not in valid_types:
            raise HTTPException(400, f"Invalid order type '{new_type}'. Must be one of: {', '.join(valid_types)}")
        order.type = new_type
    
    # Handle customer_id (integer field)
    if "customer_id" in data:
        # Validate customer exists
        customer = db.get(Customer, data["customer_id"])
        if not customer:
            raise HTTPException(400, f"Customer with ID {data['customer_id']} not found")
        order.customer_id = data["customer_id"]
    
    # Handle basic string/text fields
    for k in ["notes", "status", "delivery_date"]:
        if k in data:
            setattr(order, k, data[k])

    # Handle money fields that can be set directly (fees and charges)
    settable_money_fields = [
        "discount",
        "delivery_fee", 
        "return_delivery_fee",
        "penalty_fee",
        "paid_amount",
    ]
    for k in settable_money_fields:
        if k in data:
            setattr(order, k, Decimal(str(data[k])))
    
    # Note: subtotal, total, and balance are calculated by recompute_financials()
    # Don't allow direct setting to prevent inconsistencies

    if "plan" in data and order.plan:
        plan_patch = data["plan"]
        if "monthly_amount" in plan_patch:
            order.plan.monthly_amount = Decimal(str(plan_patch["monthly_amount"]))
        for k in ["plan_type", "months", "status"]:
            if k in plan_patch:
                setattr(order.plan, k, plan_patch[k])
        if plan_patch.get("start_date"):
            try:
                order.plan.start_date = datetime.fromisoformat(plan_patch["start_date"]).date()
            except Exception:
                pass

    if "delete_items" in data:
        for iid in data["delete_items"]:
            item = next((it for it in order.items if it.id == iid), None)
            if item:
                order.items.remove(item)
                db.delete(item)

    if "items" in data:
        for ip in data["items"]:
            iid = ip.get("id")
            if iid:
                item = next((it for it in order.items if it.id == iid), None)
                if not item:
                    continue
                for k in ["name", "item_type", "sku", "category"]:
                    if k in ip:
                        setattr(item, k, ip[k])
                if "qty" in ip:
                    item.qty = int(ip["qty"])
                for k in ["unit_price", "line_total"]:
                    if k in ip:
                        setattr(item, k, Decimal(str(ip[k])))
            else:
                name = (ip.get("name") or "").strip() or "Item"
                item_type = (ip.get("item_type") or "OUTRIGHT").strip().upper()
                sku = ip.get("sku")
                category = ip.get("category")
                qty = int(ip.get("qty") or 0)
                unit_price = Decimal(str(ip.get("unit_price") or 0))
                lt_input = ip.get("line_total")
                line_total = Decimal(str(lt_input)) if lt_input is not None else unit_price * qty
                if item_type in {"RENTAL", "INSTALLMENT"}:
                    if lt_input is not None and Decimal(str(lt_input)) > 0:
                        raise HTTPException(400, "Plan items cannot have positive totals")
                    if line_total >= 0:
                        unit_price = Decimal("0")
                        line_total = Decimal("0")
                order.items.append(
                    OrderItem(
                        name=name,
                        item_type=item_type,
                        sku=sku,
                        category=category,
                        qty=qty,
                        unit_price=unit_price,
                        line_total=line_total,
                    )
                )


    # Recompute monetary totals based on current state
    if order.plan:
        ensure_plan_first_month_fee(order)  # Currently a no-op
    # Always recompute financials after changes to ensure totals are correct
    recompute_financials(order)
    
    try:
        print(f"DEBUG: About to commit changes for order {order_id}")
        db.commit()
        print(f"DEBUG: Successfully committed changes for order {order_id}")
        db.refresh(order)
        print(f"DEBUG: Order {order_id} after refresh: status={order.status}, notes={order.notes}")
    except Exception as e:
        print(f"ERROR: Failed to commit changes for order {order_id}: {e}")
        db.rollback()
        raise HTTPException(500, f"Database error: {e}")
    
    return envelope(OrderOut.model_validate(order))


@router.post("/{order_id}/assign", response_model=dict)
def assign_order(
    order_id: int,
    body: AssignDriverIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    from datetime import date
    from ..models.driver_route import DriverRoute
    from sqlalchemy import and_
    
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    driver = db.get(Driver, body.driver_id)
    if not driver:
        raise HTTPException(404, "Driver not found")
    
    # Get or create daily route for driver
    today = date.today()
    route = (
        db.query(DriverRoute)
        .filter(
            and_(
                DriverRoute.driver_id == driver.id,
                DriverRoute.route_date == today
            )
        )
        .first()
    )
    
    route_created = False
    if not route:
        route = DriverRoute(
            driver_id=driver.id,
            route_date=today,
            name=f"{driver.name or 'Driver'} - {today.strftime('%b %d')}",
            notes=f"Manual assignment route for {driver.name or f'Driver {driver.id}'}"
        )
        db.add(route)
        db.flush()
        route_created = True
    
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if trip:
        if trip.status in {"DELIVERED", "SUCCESS"}:
            raise HTTPException(400, "Delivered orders cannot be reassigned")
        trip.driver_id = driver.id
        trip.route_id = route.id
        trip.status = "ASSIGNED"
    else:
        trip = Trip(
            order_id=order.id, 
            driver_id=driver.id, 
            route_id=route.id,
            status="ASSIGNED"
        )
        db.add(trip)
    
    # Don't change order.status - follow manual pattern
    db.commit()
    db.refresh(trip)
    log_action(db, current_user, "order.assign_driver", f"order_id={order.id},driver_id={driver.id},route_id={route.id}")
    notify_order_assigned(db, driver.id, order)
    return envelope({
        "order_id": order.id, 
        "driver_id": driver.id, 
        "trip_id": trip.id,
        "route_id": route.id,
        "route_created": route_created
    })


@router.post("/{order_id}/assign-second-driver", response_model=dict)
def assign_second_driver(
    order_id: int,
    body: AssignSecondDriverIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    driver_2 = db.get(Driver, body.driver_id_2)
    if not driver_2:
        raise HTTPException(404, "Second driver not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")
    if trip.status in {"DELIVERED", "SUCCESS"}:
        raise HTTPException(400, "Completed trips cannot have second driver assigned")
    
    # Assign the second driver
    trip.driver_id_2 = driver_2.id
    db.commit()
    db.refresh(trip)
    
    log_action(db, current_user, "order.assign_second_driver", f"order_id={order.id},driver_id_2={driver_2.id}")
    notify_order_assigned(db, driver_2.id, order)
    return envelope({"order_id": order.id, "driver_id_2": driver_2.id, "trip_id": trip.id})


class CommissionUpdateIn(BaseModel):
    amount: Decimal


@router.post("/{order_id}/success", response_model=dict)
def mark_success(
    order_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if not trip or trip.status != "DELIVERED":
        raise HTTPException(400, "Trip not delivered")
    # Flat commission rate: RM30 total, split among drivers
    rate = Decimal("30")
    # Clear existing commissions for this trip
    db.query(Commission).filter_by(trip_id=trip.id).delete()
    
    # Calculate commission per driver (split if dual drivers)
    driver_ids = trip.driver_ids
    commission_per_driver = rate / len(driver_ids)
    
    now = datetime.utcnow()
    commissions = []
    
    # Create commission for each driver
    for driver_id in driver_ids:
        commission = Commission(
            driver_id=driver_id,
            trip_id=trip.id,
            scheme="FLAT",
            rate=rate,
            computed_amount=commission_per_driver,
            actualized_at=now,
            actualization_reason="manual_success",
        )
        db.add(commission)
        commissions.append(commission)
    
    trip.status = "SUCCESS"
    db.commit()
    
    total_amount = sum(float(c.computed_amount) for c in commissions)
    commission_ids = [c.id for c in commissions]
    
    log_action(db, current_user, "order.success", f"order_id={order.id}")
    return envelope({
        "commission_ids": commission_ids, 
        "total_amount": total_amount,
        "drivers_count": len(driver_ids)
    })


@router.patch("/{order_id}/commission", response_model=dict)
def update_commission(
    order_id: int,
    body: CommissionUpdateIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.CASHIER)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
    if not trip:
        raise HTTPException(404, "Trip not found")
    # Clear existing commissions for this trip
    db.query(Commission).filter_by(trip_id=trip.id).delete()
    
    # Calculate commission per driver (split if dual drivers)
    driver_ids = trip.driver_ids
    amt = to_decimal(body.amount)
    commission_per_driver = amt / len(driver_ids)
    
    commissions = []
    # Create commission for each driver
    for driver_id in driver_ids:
        commission = Commission(
            driver_id=driver_id,
            trip_id=trip.id,
            scheme="FLAT",
            rate=amt,
            computed_amount=commission_per_driver,
        )
        db.add(commission)
        commissions.append(commission)
    
    db.commit()
    
    total_amount = sum(float(c.computed_amount) for c in commissions)
    commission_ids = [c.id for c in commissions]
    
    log_action(db, current_user, "commission.update", f"commission_ids={commission_ids}")
    return envelope({
        "commission_ids": commission_ids,
        "total_amount": total_amount,
        "drivers_count": len(driver_ids)
    })


@router.post("/{order_id}/void", response_model=dict)
def void_order(
    order_id: int,
    body: dict | None = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    import uuid
    
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    # Generate idempotency key if not provided
    if idempotency_key is None:
        idempotency_key = f"void_order_{order_id}_{uuid.uuid4().hex[:8]}"

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope({"order_id": order.id, "status": order.status})

    reason = (body or {}).get("reason") if body else None
    try:
        mark_cancelled(db, order, reason)
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="void"))
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope({"order_id": order.id, "status": order.status})


class ReturnIn(BaseModel):
    date: str | None = None
    return_delivery_fee: Decimal | None = None
    collect: bool | None = False
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/return", response_model=dict)
def return_order(
    order_id: int,
    body: ReturnIn | None = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    ret_date = None
    if body and body.date:
        try:
            ret_date = datetime.fromisoformat(body.date)
        except Exception:
            ret_date = None
    try:
        mark_returned(
            db,
            order,
            ret_date,
            body.return_delivery_fee if body else None,
            bool(body.collect) if body else False,
            body.method if body else None,
            body.reference if body else None,
            date_cls.fromisoformat(body.date) if body and body.date else None,
        )
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="return"))
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))




class DiscountIn(BaseModel):
    type: str
    value: Decimal


class BuybackIn(BaseModel):
    amount: Decimal
    discount: DiscountIn | None = None
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/buyback", response_model=dict)
def buyback_order(
    order_id: int,
    body: BuybackIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    try:
        discount = body.discount.model_dump() if body.discount else None
        apply_buyback(
            db,
            order,
            Decimal(str(body.amount)),
            discount,
            body.method,
            body.reference,
        )
        db.add(IdempotentRequest(key=idempotency_key, order_id=order.id, action="buyback"))
        db.commit()
        db.refresh(order)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))


class CancelInstallmentIn(BaseModel):
    penalty: Decimal | None = None
    return_delivery_fee: Decimal | None = None
    collect: bool | None = False
    method: str | None = None
    reference: str | None = None


@router.post("/{order_id}/cancel-installment", response_model=dict)
def cancel_installment_order(
    order_id: int,
    body: CancelInstallmentIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    existing = db.query(IdempotentRequest).filter_by(key=idempotency_key).one_or_none()
    if existing:
        return envelope(OrderOut.model_validate(order))

    try:
        cancel_installment(
            db,
            order,
            body.penalty,
            body.return_delivery_fee,
            bool(body.collect) if body.collect is not None else False,
            body.method,
            body.reference,
        )
        db.add(
            IdempotentRequest(key=idempotency_key, order_id=order.id, action="cancel_installment")
        )
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return envelope(OrderOut.model_validate(order))





class SimpleOrderIn(BaseModel):
    customer_name: str
    customer_phone: str | None = None
    delivery_address: str
    notes: str | None = None
    total_amount: float
    delivery_date: str | None = None


@router.post("/simple", response_model=dict, status_code=201)
def create_simple_order(
    body: SimpleOrderIn,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    """Create a simple order for admin use (from message parsing)"""
    try:
        # Create customer first
        customer = Customer(
            name=body.customer_name,
            phone=body.customer_phone or "",
            address=body.delivery_address
        )
        db.add(customer)
        db.flush()  # Get customer ID
        
        # Parse delivery date if provided
        delivery_date = None
        if body.delivery_date:
            try:
                delivery_date = datetime.fromisoformat(body.delivery_date.replace('Z', '+00:00'))
            except:
                delivery_date = None
        
        # Create order
        order = Order(
            customer_id=customer.id,
            customer_name=body.customer_name,
            customer_phone=body.customer_phone,
            delivery_address=body.delivery_address,
            notes=body.notes,
            total_amount=Decimal(str(body.total_amount)),
            delivery_date=delivery_date,
            status="PENDING",
            created_at=datetime.now(timezone.utc)
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        log_action(db, current_user.id, "create_simple_order", f"Order #{order.id}")
        
        # Trigger auto-assignment after order creation (use AssignmentService directly)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"About to trigger auto-assignment for simple order {order.id}")
        print(f"About to trigger auto-assignment for simple order {order.id}")
        
        try:
            from ..services.assignment_service import AssignmentService
            assignment_service = AssignmentService(db)
            trigger_result = assignment_service.auto_assign_all()
            logger.info(f"Auto-assignment completed for simple order {order.id}: {trigger_result}")
            print(f"Auto-assignment completed for simple order {order.id}: {trigger_result}")
        except Exception as e:
            logger.error(f"Auto-assignment failed for simple order {order.id}: {e}")
            print(f"Auto-assignment failed for simple order {order.id}: {e}")
            # Don't fail order creation if assignment fails
            trigger_result = {"success": False, "error": str(e)}
        
        return {
            "id": order.id,
            "code": order.code,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "status": order.status,
            "total_amount": float(order.total_amount) if order.total_amount else 0,
            "notes": order.notes,
            "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
            "created_at": order.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Create failed: {e}")
