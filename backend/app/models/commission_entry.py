from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    ForeignKey,
    Numeric,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CommissionEntry(Base):
    __tablename__ = "commission_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("driver_shifts.id"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    
    # Entry details
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)  # DELIVERY, OUTSTATION_ALLOWANCE
    amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Role and status
    driver_role: Mapped[str | None] = mapped_column(String(20), nullable=True)  # primary, secondary
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="EARNED")  # EARNED, PAID
    
    # Commission calculation details (for delivery entries)
    base_commission_rate: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)  # e.g., 0.10 for 10%
    order_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    commission_scheme: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Metadata
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    driver = relationship("Driver", back_populates="commission_entries")
    shift = relationship("DriverShift", back_populates="commission_entries")
    order = relationship("Order")
    trip = relationship("Trip")

    @property
    def is_outstation_allowance(self) -> bool:
        """Check if this entry is an outstation allowance"""
        return self.entry_type == "OUTSTATION_ALLOWANCE"
    
    @property
    def is_delivery_commission(self) -> bool:
        """Check if this entry is a delivery commission"""
        return self.entry_type == "DELIVERY"