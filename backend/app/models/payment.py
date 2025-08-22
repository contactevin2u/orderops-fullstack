from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, String, Numeric, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # cash/transfer/cheque/etc
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(20), default="ORDER")  # ORDER|RENTAL|INSTALLMENT|PENALTY|DELIVERY|BUYBACK
    status: Mapped[str] = mapped_column(String(20), default="POSTED")  # POSTED|VOIDED
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
