from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..auth.firebase import driver_auth
from ..db import get_session
from ..models import Trip, TripEvent, Order
from ..schemas import TripOut
from ..services.notifications import notify_trip_assignment
from ..services.status_updates import recompute_financials
from ..utils.responses import envelope

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=dict)
def list_trips(db: Session = Depends(get_session)):
    trips = (
        db.query(Trip)
        .filter(Trip.status.in_(["ASSIGNED", "IN_PROGRESS"]))
        .order_by(Trip.created_at.desc())
        .all()
    )
    data = [TripOut.model_validate(t) for t in trips]
    return envelope(data)


@router.get("/active", response_model=dict)
def list_active_trips(
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trips = (
        db.query(Trip)
        .filter(Trip.driver_id == driver.id)
        .filter(Trip.status.in_(["ASSIGNED", "IN_PROGRESS"]))
        .order_by(Trip.planned_at)
        .all()
    )
    data = [TripOut.model_validate(t) for t in trips]
    return envelope(data)


class FailIn(BaseModel):
    reason: str | None = None


@router.post("/{trip_id}/start", response_model=dict)
def start_trip(
    trip_id: int,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_id != driver.id:
        raise HTTPException(404, "Trip not found")
    trip.status = "IN_PROGRESS"
    trip.started_at = datetime.now(timezone.utc)
    db.add(TripEvent(trip_id=trip.id, status="STARTED"))
    db.commit()
    return envelope({"status": trip.status})


@router.post("/{trip_id}/deliver", response_model=dict)
def deliver_trip(
    trip_id: int,
    photo: UploadFile | None = File(None),
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_id != driver.id:
        raise HTTPException(404, "Trip not found")
    trip.status = "DELIVERED"
    trip.delivered_at = datetime.now(timezone.utc)
    if photo:
        path = f"pod_{trip.id}_{photo.filename}"
        with open(path, "wb") as f:
            f.write(photo.file.read())
        trip.pod_photo_url = path
    db.add(TripEvent(trip_id=trip.id, status="DELIVERED"))
    order = db.get(Order, trip.order_id)
    if order:
        recompute_financials(order)
    db.commit()
    return envelope({"status": trip.status, "pod_photo_url": trip.pod_photo_url})


@router.post("/{trip_id}/fail", response_model=dict)
def fail_trip(
    trip_id: int,
    body: FailIn,
    driver=Depends(driver_auth),
    db: Session = Depends(get_session),
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_id != driver.id:
        raise HTTPException(404, "Trip not found")
    trip.status = "FAILED"
    trip.failure_reason = body.reason or ""
    db.add(TripEvent(trip_id=trip.id, status="FAILED", note=body.reason))
    order = db.get(Order, trip.order_id)
    if order:
        recompute_financials(order)
    db.commit()
    return envelope({"status": trip.status})


class AssignIn(BaseModel):
    driver_id: int


@router.post("/{trip_id}/assign", response_model=dict)
def assign_trip(trip_id: int, body: AssignIn, db: Session = Depends(get_session)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    trip.driver_id = body.driver_id
    trip.status = "ASSIGNED"
    notify_trip_assignment(db, trip)
    db.commit()
    return envelope({"status": trip.status})


@router.post("/{trip_id}/notify", response_model=dict)
def resend_notification(trip_id: int, db: Session = Depends(get_session)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "Trip not found")
    count = notify_trip_assignment(db, trip)
    return envelope({"sent": count})
