from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base
import enum


class ItemStatus(enum.Enum):
    WAREHOUSE = "WAREHOUSE"           # In warehouse
    WITH_DRIVER = "WITH_DRIVER"       # Loaded on driver's truck
    DELIVERED = "DELIVERED"           # Delivered to customer
    RETURNED = "RETURNED"             # Returned to warehouse
    IN_REPAIR = "IN_REPAIR"           # Sent for repair
    DISCONTINUED = "DISCONTINUED"      # No longer in use


class ItemType(enum.Enum):
    NEW = "NEW"           # New item (requires 2 UID copies)
    RENTAL = "RENTAL"     # Rental item (1 UID sticker on item)


class Item(Base):
    __tablename__ = "item"
    
    uid = Column(String, primary_key=True)
    sku_id = Column(Integer, ForeignKey("sku.id"), nullable=False)
    item_type = Column(SQLEnum(ItemType), nullable=False, default=ItemType.RENTAL)
    copy_number = Column(Integer, nullable=True)  # 1 or 2 for NEW items, NULL for RENTAL
    oem_serial = Column(String, nullable=True)
    status = Column(SQLEnum(ItemStatus), nullable=False, default=ItemStatus.WAREHOUSE)
    current_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # Relationships
    sku = relationship("SKU", back_populates="items")
    current_driver = relationship("Driver", foreign_keys=[current_driver_id])
    order_items = relationship("OrderItemUID", back_populates="item")