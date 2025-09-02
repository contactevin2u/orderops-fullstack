from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Order, Trip, OrderItem, Plan
from ..routers.orders import OrderPatch
from ..schemas import OrderOut
from ..utils.responses import envelope
from ..services.ordersvc import recompute_financials

router = APIRouter(prefix="/orders", tags=["driver-orders"])


class UpsellItemRequest(BaseModel):
    item_id: int
    upsell_type: str  # "BELI_TERUS" | "ANSURAN"
    new_name: str | None = None
    new_price: float  # New total price for the item
    installment_months: int | None = None  # Only for ANSURAN


class UpsellRequest(BaseModel):
    items: list[UpsellItemRequest]
    notes: str | None = None


@router.patch("/{order_id}/driver-update", response_model=dict)
def driver_update_order(
    order_id: int, 
    body: OrderPatch, 
    driver=Depends(driver_auth), 
    db: Session = Depends(get_session)
):
    """Allow drivers to update orders they're assigned to"""
    try:
        # First, verify the driver is assigned to this order
        trip = (
            db.query(Trip)
            .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
            .one_or_none()
        )
        if not trip:
            raise HTTPException(404, "Order not found or not assigned to you")

        order = db.get(Order, order_id)
        if not order:
            raise HTTPException(404, "Order not found")

        data = body.model_dump(exclude_none=True)
        
        # Handle ON_HOLD special case: customer requested reschedule
        if data.get("status") == "ON_HOLD":
            # Update delivery_date if provided
            if data.get("delivery_date"):
                try:
                    if isinstance(data["delivery_date"], str):
                        parsed_date = datetime.fromisoformat(data["delivery_date"].replace('Z', '+00:00'))
                        order.delivery_date = parsed_date
                except ValueError:
                    raise HTTPException(400, f"Invalid date format: {data['delivery_date']}")
            
            # Make trip available for reassignment while keeping current driver info for audit
            trip.status = "UNASSIGNED"
            trip.route_id = None
            # Keep driver_id for audit trail, assignment service will update when reassigning
            # Order status remains unchanged - no need to modify order status
            
        else:
            # Only allow drivers to update specific fields for other operations
            allowed_fields = ["status", "delivery_date", "notes"]
            
            for k in allowed_fields:
                if k in data:
                    if k == "delivery_date" and data[k]:
                        try:
                            # Parse the date string to datetime
                            if isinstance(data[k], str):
                                parsed_date = datetime.fromisoformat(data[k].replace('Z', '+00:00'))
                                setattr(order, k, parsed_date)
                            else:
                                setattr(order, k, data[k])
                        except ValueError:
                            raise HTTPException(400, f"Invalid date format: {data[k]}")
                    else:
                        setattr(order, k, data[k])
    
        db.commit()
        db.refresh(order)
        return envelope(OrderOut.model_validate(order))
    except Exception as e:
        db.rollback()
        print(f"DEBUG: ON_HOLD error for order {order_id}: {e}")
        print(f"DEBUG: Request data: {body.model_dump(exclude_none=True)}")
        raise HTTPException(400, f"Failed to update order: {str(e)}")


@router.post("/{order_id}/upsell", response_model=dict)
def upsell_order_items(
    order_id: int,
    body: UpsellRequest,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session)
):
    """Allow drivers to upsell items in orders they're assigned to"""
    # Verify driver is assigned to this order
    trip = (
        db.query(Trip)
        .filter(Trip.order_id == order_id, Trip.driver_id == driver.id)
        .one_or_none()
    )
    if not trip:
        raise HTTPException(404, "Order not found or not assigned to you")

    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    
    # Check if order is in a valid state for upselling
    if order.status not in ["NEW", "ACTIVE", "PENDING"]:
        raise HTTPException(400, f"Cannot upsell order with status: {order.status}")
    
    has_installment_upsells = False
    
    # Process each item upsell
    for upsell_item in body.items:
        # Find the item
        item = next((it for it in order.items if it.id == upsell_item.item_id), None)
        if not item:
            raise HTTPException(400, f"Item with ID {upsell_item.item_id} not found in order")
        
        # Update item name if provided
        if upsell_item.new_name:
            item.name = upsell_item.new_name
        
        new_price = Decimal(str(upsell_item.new_price))
        
        if upsell_item.upsell_type == "BELI_TERUS":
            # Upgrade to outright purchase at new price
            item.item_type = "OUTRIGHT"
            item.unit_price = new_price / item.qty  # Calculate unit price
            item.line_total = new_price
            
        elif upsell_item.upsell_type == "ANSURAN":
            # Convert to installment plan
            if not upsell_item.installment_months:
                raise HTTPException(400, "installment_months required for ANSURAN")
            
            item.item_type = "INSTALLMENT"
            item.unit_price = new_price / item.qty  # Store original unit price
            item.line_total = Decimal("0")  # Installment items have 0 line_total
            has_installment_upsells = True
    
    # Create or update installment plan if any items were converted
    if has_installment_upsells:
        # Get the first installment item for plan details
        installment_item = next(
            (upsell for upsell in body.items 
             if upsell.upsell_type == "ANSURAN" and upsell.installment_months), 
            None
        )
        
        if installment_item:
            # Calculate monthly amount: new_price / months
            monthly_amount = Decimal(str(installment_item.new_price)) / installment_item.installment_months
            
            if not order.plan:
                # Create new plan
                plan = Plan(
                    order_id=order.id,
                    plan_type="INSTALLMENT",
                    months=installment_item.installment_months,
                    monthly_amount=monthly_amount,
                    start_date=datetime.now().date(),
                    status="ACTIVE"
                )
                order.plan = plan
            else:
                # Update existing plan
                order.plan.plan_type = "INSTALLMENT"
                order.plan.months = installment_item.installment_months
                order.plan.monthly_amount = monthly_amount
        
        # Update order type to include installment
        if order.type == "OUTRIGHT":
            order.type = "INSTALLMENT"
        elif order.type == "RENTAL":
            order.type = "MIXED"  # Both rental and installment
        elif order.type != "INSTALLMENT":
            order.type = "MIXED"
    
    # Add upsell notes
    if body.notes:
        existing_notes = order.notes or ""
        upsell_note = f"[UPSELL by {driver.name}] {body.notes}"
        order.notes = f"{existing_notes}\n{upsell_note}".strip()
    
    # Recalculate order financials
    recompute_financials(order)
    
    db.commit()
    db.refresh(order)
    
    return envelope({
        "success": True,
        "order_id": order.id,
        "message": f"Successfully upsold {len(body.items)} items",
        "new_total": str(order.total),
        "order": OrderOut.model_validate(order)
    })