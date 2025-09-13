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


class DriverShift(Base):
    __tablename__ = "driver_shifts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    
    # Clock-in details
    clock_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_in_lat: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    clock_in_lng: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    clock_in_location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Clock-out details (nullable until shift ends)
    clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clock_out_lat: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    clock_out_lng: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    clock_out_location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Outstation tracking
    is_outstation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outstation_distance_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    outstation_allowance_amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    
    # Working hours calculation
    total_working_hours: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    
    # Status and metadata
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, COMPLETED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    driver = relationship("Driver", back_populates="shifts")
    commission_entries = relationship("CommissionEntry", back_populates="shift")
    lorry_assignment = relationship("LorryAssignment", back_populates="shift")

    @property
    def is_active(self) -> bool:
        """Check if shift is currently active (not clocked out)"""
        return self.status == "ACTIVE" and self.clock_out_at is None
    
    @property
    def shift_duration_hours(self) -> float | None:
        """Calculate shift duration in hours"""
        if not self.clock_out_at:
            return None
        
        duration = self.clock_out_at - self.clock_in_at
        return duration.total_seconds() / 3600