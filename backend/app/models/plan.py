from sqlalchemy import BigInteger, Date, String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(20))  # RENTAL | INSTALLMENT
    start_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    months: Mapped[int | None] = mapped_column(Numeric(12,0), nullable=True)  # For installment
    monthly_amount: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE|CANCELLED|COMPLETED
