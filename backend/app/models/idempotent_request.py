from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class IdempotentRequest(Base):
    __tablename__ = "idempotent_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order = relationship("Order")
