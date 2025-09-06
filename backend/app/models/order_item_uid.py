from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, CheckConstraint, UniqueConstraint, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from .base import Base
import enum


class UIDAction(enum.Enum):
    LOAD_OUT = "LOAD_OUT"      # Driver loading items from warehouse
    DELIVER = "DELIVER"        # Item delivered to customer
    RETURN = "RETURN"          # Customer return
    REPAIR = "REPAIR"          # Item sent for repair
    SWAP = "SWAP"             # Item swap (old for new)
    LOAD_IN = "LOAD_IN"       # Driver returning items to warehouse
    ISSUE = "ISSUE"           # Legacy - maintain compatibility


class OrderItemUID(Base):
    __tablename__ = "order_item_uid"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)
    uid = Column(String, ForeignKey("item.uid"), nullable=False)
    scanned_by = Column(Integer, ForeignKey("driver.id"), nullable=False)
    scanned_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    action = Column(SQLEnum(UIDAction), nullable=False)
    sku_id = Column(Integer, ForeignKey("sku.id"), nullable=True)  # For manual entry
    sku_name = Column(String, nullable=True)  # Cache for display
    notes = Column(Text, nullable=True)
    
    # Constraints - Remove unique constraint to allow multiple scans
    __table_args__ = ()
    
    # Relationships
    order = relationship("Order", back_populates="item_uids")
    item = relationship("Item", back_populates="order_items")
    driver = relationship("Driver", back_populates="scanned_items")
    sku = relationship("SKU")