from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .base import Base


class LorryStock(Base):
    __tablename__ = "lorry_stock"
    
    driver_id = Column(Integer, ForeignKey("drivers.id"), primary_key=True)
    as_of_date = Column(Date, primary_key=True)
    sku_id = Column(Integer, ForeignKey("sku.id"), primary_key=True)
    qty_counted = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    uploaded_by = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    
    # Relationships
    driver = relationship("Driver", foreign_keys=[driver_id], back_populates="lorry_stocks")
    uploader = relationship("Driver", foreign_keys=[uploaded_by])
    sku = relationship("SKU", back_populates="lorry_stocks")