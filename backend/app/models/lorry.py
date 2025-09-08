from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Boolean,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Lorry(Base):
    """Lorry/Vehicle management"""
    __tablename__ = "lorries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lorry_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # e.g., "LRY001"
    plate_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "1 ton", "500kg"
    
    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Location and warehouse
    base_warehouse: Mapped[str] = mapped_column(String(20), default="BATU_CAVES", nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Maintenance and notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_maintenance_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Lorry(lorry_id={self.lorry_id}, plate_number={self.plate_number}, is_active={self.is_active})>"