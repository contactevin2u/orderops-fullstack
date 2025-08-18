from sqlalchemy import BigInteger, DateTime, String, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50))  # BED | WHEELCHAIR | OXYGEN | ACCESSORY
    item_type: Mapped[str] = mapped_column(String(20))  # OUTRIGHT|INSTALLMENT|RENTAL|FEE
    qty: Mapped[int] = mapped_column(Numeric(12,0), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12,2), default=0)
