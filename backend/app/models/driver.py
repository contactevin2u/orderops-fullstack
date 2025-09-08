from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    base_warehouse: Mapped[str] = mapped_column(String(20), default="BATU_CAVES", nullable=False)  # BATU_CAVES | KOTA_KINABALU
    priority_lorry_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)  # Preferred lorry assignment
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    devices = relationship("DriverDevice", back_populates="driver", cascade="all, delete-orphan")
    shifts = relationship("DriverShift", back_populates="driver")
    commission_entries = relationship("CommissionEntry", back_populates="driver")
    schedules = relationship("DriverSchedule", back_populates="driver")
    availability_patterns = relationship("DriverAvailabilityPattern", back_populates="driver")
    scanned_items = relationship("OrderItemUID", back_populates="driver")
    lorry_stocks = relationship("LorryStock", foreign_keys="LorryStock.driver_id", back_populates="driver")
    lorry_assignments = relationship("LorryAssignment", back_populates="driver")
    holds = relationship("DriverHold", back_populates="driver")


class DriverDevice(Base):
    __tablename__ = "driver_devices"
    __table_args__ = (
        UniqueConstraint("driver_id", "token", name="uq_driver_devices_driver_id_token"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20))
    app_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    driver = relationship("Driver", back_populates="devices")
