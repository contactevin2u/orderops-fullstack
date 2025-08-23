from datetime import datetime
from sqlalchemy.orm import Session

from ..models import Trip, Commission, Payment


def maybe_actualize_commission(db: Session, trip_id: int) -> None:
    trip = db.get(Trip, trip_id)
    if not trip or trip.status != "DELIVERED":
        return
    commission = db.query(Commission).filter_by(trip_id=trip_id).one_or_none()
    if not commission or commission.actualized_at:
        return
    has_payment = (
        db.query(Payment)
        .filter(Payment.order_id == trip.order_id, Payment.status == "POSTED")
        .count()
        > 0
    )
    if has_payment:
        commission.actualized_at = datetime.utcnow()
        commission.actualization_reason = "delivered+first_payment"
        db.add(commission)
        db.commit()
