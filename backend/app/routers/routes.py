from datetime import date as dt_date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_session
from ..models import DriverRoute, Trip, Order, Driver, Role
from ..schemas import RouteCreateIn, RouteOut, RouteUpdateIn, RouteStopOut
from ..auth.deps import require_roles

router = APIRouter(
    prefix="/routes",
    tags=["routes"],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))],
)


@router.post("", response_model=RouteOut)
def create_route(payload: RouteCreateIn, db: Session = Depends(get_session)):
    driver = db.get(Driver, payload.driver_id)
    if not driver:
        raise HTTPException(404, "Driver not found")
    r = DriverRoute(
        driver_id=driver.id,
        route_date=dt_date.fromisoformat(payload.route_date),
        name=payload.name,
        notes=payload.notes,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.patch("/{route_id}", response_model=RouteOut)
def update_route(route_id: int, payload: RouteUpdateIn, db: Session = Depends(get_session)):
    route = db.get(DriverRoute, route_id)
    if not route:
        raise HTTPException(404, "Route not found")
    if payload.driver_id is not None:
        driver = db.get(Driver, payload.driver_id)
        if not driver:
            raise HTTPException(404, "Driver not found")
        
        # Update route driver
        old_driver_id = route.driver_id
        route.driver_id = driver.id
        
        # CRITICAL: Update all trips on this route to new driver
        trips_updated = db.query(Trip).filter(Trip.route_id == route_id).update(
            {Trip.driver_id: driver.id},
            synchronize_session=False
        )
        
        # Alternative method if bulk update fails
        if trips_updated == 0:
            trips_on_route = db.query(Trip).filter(Trip.route_id == route_id).all()
            for trip in trips_on_route:
                trip.driver_id = driver.id
            trips_updated = len(trips_on_route)
        
        print(f"Route {route_id}: Changed driver from {old_driver_id} to {driver.id}, updated {trips_updated} trips")
    if payload.route_date is not None:
        route.route_date = dt_date.fromisoformat(payload.route_date)
    if payload.name is not None:
        route.name = payload.name
    if payload.notes is not None:
        route.notes = payload.notes
    db.commit()
    db.refresh(route)
    return route


@router.get("", response_model=list[RouteOut])
def list_routes(date: str | None = None, db: Session = Depends(get_session)):
    q = db.query(DriverRoute)
    if date:
        try:
            d = dt_date.fromisoformat(date)
        except ValueError:
            raise HTTPException(400, "Invalid date format")
        q = q.filter(DriverRoute.route_date == d)
    
    routes = q.order_by(DriverRoute.route_date.desc(), DriverRoute.id.desc()).all()
    
    # Enrich each route with stops data
    result = []
    for route in routes:
        # Get trips/orders for this route
        trips = db.query(Trip).filter(Trip.route_id == route.id).order_by(Trip.id).all()
        
        # Get secondary driver ID from trips (if any trip has one)
        secondary_driver_id = None
        for trip in trips:
            if trip.driver_id_2:
                secondary_driver_id = trip.driver_id_2
                break
        
        # Create stops data
        stops = []
        for i, trip in enumerate(trips):
            stops.append(RouteStopOut(
                orderId=str(trip.order_id),
                seq=i + 1
            ))
        
        # Create route response with stops
        route_data = RouteOut(
            id=route.id,
            driver_id=route.driver_id,
            driver_id_2=secondary_driver_id,  # Get from trips
            route_date=route.route_date,
            name=route.name,
            notes=route.notes,
            stops=stops
        )
        result.append(route_data)
    
    return result


@router.get("/{route_id}/orders", response_model=list[dict])
def get_route_orders(route_id: int, db: Session = Depends(get_session)):
    """Get all orders/trips for a specific route"""
    route = db.get(DriverRoute, route_id)
    if not route:
        raise HTTPException(404, "Route not found")
    
    # Join Trip with Order and Customer to get complete data including addresses
    from sqlalchemy.orm import joinedload
    from ..models import Customer
    
    trips = (
        db.query(Trip)
        .options(joinedload(Trip.order).joinedload(Order.customer))
        .filter(Trip.route_id == route_id)
        .order_by(Trip.id)
        .all()
    )
    
    orders_data = []
    for trip in trips:
        order = trip.order
        customer = order.customer if order else None
        
        # Build order data similar to the main orders endpoint
        order_data = {
            "id": order.id if order else None,
            "code": order.code if order else None,
            "status": trip.status,
            "delivery_date": order.delivery_date.isoformat() if order and order.delivery_date else None,
            "address": customer.address if customer else None,  # Get address from customer
            "customer_name": customer.name if customer else None,
            "customer_address": customer.address if customer else None,
            "customer_phone": customer.phone if customer else None,
            "total": float(order.total) if order and order.total else 0,
            "trip": {
                "id": trip.id,
                "status": trip.status,
                "route_id": trip.route_id,
                "driver_id": trip.driver_id,
                "driver_id_2": trip.driver_id_2
            }
        }
        orders_data.append(order_data)
    
    return orders_data

@router.post("/{route_id}/orders", response_model=dict)
def add_orders_to_route(route_id: int, body: dict, db: Session = Depends(get_session)):
    order_ids: list[int] = body.get("order_ids") or []
    route = db.get(DriverRoute, route_id)
    if not route:
        raise HTTPException(404, "Route not found")

    assigned, skipped = [], []
    for oid in order_ids:
        order = db.get(Order, oid)
        if not order:
            skipped.append((oid, "order_not_found"))
            continue
        trip = db.query(Trip).filter_by(order_id=order.id).one_or_none()
        if trip:
            if trip.status in {"DELIVERED", "SUCCESS"}:
                skipped.append((oid, "delivered_or_success"))
                continue
            trip.driver_id = route.driver_id
            trip.route_id = route.id
            trip.status = "ASSIGNED"
            assigned.append(oid)
        else:
            trip = Trip(
                order_id=order.id,
                driver_id=route.driver_id,
                status="ASSIGNED",
                route_id=route.id,
            )
            db.add(trip)
            assigned.append(oid)
    db.commit()
    return {"assigned": assigned, "skipped": skipped}


@router.delete("/{route_id}/orders", response_model=dict)
def remove_orders_from_route(
    route_id: int, body: dict, db: Session = Depends(get_session)
):
    order_ids: list[int] = body.get("order_ids") or []
    route = db.get(DriverRoute, route_id)
    if not route:
        raise HTTPException(404, "Route not found")

    removed, skipped = [], []
    for oid in order_ids:
        trip = db.query(Trip).filter_by(order_id=oid, route_id=route.id).one_or_none()
        if not trip:
            skipped.append((oid, "not_on_route"))
            continue
        trip.route_id = None
        removed.append(oid)
    db.commit()
    return {"removed": removed, "skipped": skipped}
