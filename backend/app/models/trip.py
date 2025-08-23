from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    ForeignKey,
    Index,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSIGNED")
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pod_photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_trips_driver_status_planned", "driver_id", "status", "planned_at"),
    )


class TripEvent(Base):
    __tablename__ = "trip_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    lat: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
