"""Upsell record model for tracking driver upsell activities and incentives"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, BigInteger, Numeric, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UpsellRecord(Base):
    """Track upsell activities for reporting and driver incentives"""
    __tablename__ = "upsell_records"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # References
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    
    # Upsell details
    original_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    new_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    upsell_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # new_total - original_total
    
    # Items upsold (JSON-like text field)
    items_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string of upsold items
    upsell_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Driver incentive (10% of upsell amount)
    driver_incentive: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    incentive_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING, RELEASED
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    order = relationship("Order")
    driver = relationship("Driver")
    trip = relationship("Trip")