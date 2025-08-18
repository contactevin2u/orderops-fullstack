from sqlalchemy import BigInteger, DateTime, String, Text, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(20))  # OUTRIGHT | INSTALLMENT | RENTAL
    status: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW|ACTIVE|RETURNED|CANCELLED|COMPLETED
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    delivery_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtotal: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    discount: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    return_delivery_fee: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    penalty_fee: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    balance: Mapped[float] = mapped_column(Numeric(12,2), default=0)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    customer = relationship("Customer")
    items = relationship("OrderItem", cascade="all, delete-orphan")
    plan = relationship("Plan", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", cascade="all, delete-orphan")
