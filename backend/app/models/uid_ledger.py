from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base
from .order_item_uid import UIDAction
import enum


class LedgerEntrySource(enum.Enum):
    ADMIN_MANUAL = "ADMIN_MANUAL"           # Admin manually scanned in system
    DRIVER_SYNC = "DRIVER_SYNC"             # Synced from driver app
    ORDER_OPERATION = "ORDER_OPERATION"     # Part of order fulfillment
    INVENTORY_AUDIT = "INVENTORY_AUDIT"     # Inventory audit scan
    MAINTENANCE = "MAINTENANCE"             # Maintenance/repair operations
    SYSTEM_IMPORT = "SYSTEM_IMPORT"         # Bulk import/migration


class UIDLedgerEntry(Base):
    """
    Comprehensive UID scan ledger for medical device traceability.
    Records EVERY scan action across the entire system for audit purposes.
    """
    __tablename__ = "uid_ledger"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core scan information
    uid = Column(String, ForeignKey("item.uid"), nullable=False, index=True)
    action = Column(SQLEnum(UIDAction), nullable=False)
    scanned_at = Column(DateTime, nullable=False, default=func.current_timestamp(), index=True)
    
    # Who performed the scan
    scanned_by_admin = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin user
    scanned_by_driver = Column(Integer, ForeignKey("drivers.id"), nullable=True)  # Driver
    scanner_name = Column(String, nullable=True)  # Fallback name if no FK available
    
    # Context information
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Associated order (if any)
    sku_id = Column(Integer, ForeignKey("sku.id"), nullable=True)  # For manual entry
    source = Column(SQLEnum(LedgerEntrySource), nullable=False, default=LedgerEntrySource.ADMIN_MANUAL)
    
    # Location tracking
    lorry_id = Column(String, nullable=True)  # Which lorry/truck
    location_notes = Column(String, nullable=True)  # Free-form location
    
    # Additional metadata
    notes = Column(Text, nullable=True)
    customer_name = Column(String, nullable=True)  # For delivery context
    order_reference = Column(String, nullable=True)  # Order code/reference
    
    # Sync tracking (for driver app integration)
    driver_scan_id = Column(String, nullable=True, unique=True)  # Reference to driver app scan
    sync_status = Column(String, nullable=False, default="RECORDED")  # RECORDED, PENDING_DRIVER_SYNC
    
    # Audit trail
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Admin who recorded entry
    recorded_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    is_deleted = Column(Boolean, nullable=False, default=False)  # Soft delete for audit
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    # Relationships
    item = relationship("Item")
    order = relationship("Order")
    sku = relationship("SKU")
    admin_scanner = relationship("User", foreign_keys=[scanned_by_admin])
    driver_scanner = relationship("Driver", foreign_keys=[scanned_by_driver])
    recorder = relationship("User", foreign_keys=[recorded_by])
    deleter = relationship("User", foreign_keys=[deleted_by])
    
    def __repr__(self):
        return f"<UIDLedgerEntry(uid={self.uid}, action={self.action.value}, scanned_at={self.scanned_at})>"