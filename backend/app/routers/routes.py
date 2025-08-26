from datetime import date as dt_date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import DriverRoute, Trip, Order, Driver, Role
from ..schemas import RouteCreateIn, RouteOut
from ..auth.deps import require_roles

router = APIRouter(prefix="/routes", tags=["routes"], dependencies=[Depends(require_roles(Role.ADMIN, Role.CASHIER))])


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


@router.get("", response_model=list[RouteOut])
def list_routes(date: str | None = None, db: Session = Depends(get_session)):
    q = db.query(DriverRoute)
    if date:
        try:
            d = dt_date.fromisoformat(date)
        except ValueError:
            raise HTTPException(400, "Invalid date format")
        q = q.filter(DriverRoute.route_date == d)
    return q.order_by(DriverRoute.route_date.desc(), DriverRoute.id.desc()).all()


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
