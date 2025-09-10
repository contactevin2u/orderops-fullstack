from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LorryStockTransaction(Base):
    """Admin-controlled lorry stock movements and transactions"""
    __tablename__ = "lorry_stock_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lorry_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Transaction details
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # LOAD, UNLOAD, ADMIN_ADJUSTMENT, DELIVERY, COLLECTION
    uid: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    
    # Related records
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)  # For delivery actions
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)  # For delivery actions
    
    # Admin control
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Transaction metadata
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    order = relationship("Order")
    driver = relationship("Driver")
    admin_user = relationship("User")

    def __repr__(self):
        return f"<LorryStockTransaction(lorry_id={self.lorry_id}, action={self.action}, uid={self.uid})>"

    @property
    def is_stock_addition(self) -> bool:
        """Check if this transaction adds stock to the lorry"""
        return self.action in ["LOAD", "COLLECTION"]
    
    @property
    def is_stock_removal(self) -> bool:
        """Check if this transaction removes stock from the lorry"""
        return self.action in ["UNLOAD", "DELIVERY"]
    
    @property
    def is_adjustment(self) -> bool:
        """Check if this transaction is an admin adjustment (requires special handling)"""
        return self.action == "ADMIN_ADJUSTMENT"