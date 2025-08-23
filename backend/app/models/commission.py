from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    DateTime,
    Numeric,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Commission(Base):
    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id"), nullable=False, unique=True
    )
    scheme: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    computed_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    actualized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    actualization_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
