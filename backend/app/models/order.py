from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, DateTime, String, Text, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20))  # OUTRIGHT | INSTALLMENT | RENTAL | MIXED
    status: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW|ACTIVE|RETURNED|CANCELLED|COMPLETED
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    return_delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    penalty_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    customer = relationship("Customer")
    items = relationship("OrderItem", cascade="all, delete-orphan")
    plan = relationship("Plan", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", cascade="all, delete-orphan")
