from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Text
from sqlalchemy.orm import relationship
from .base import Base


class SKU(Base):
    __tablename__ = "sku"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)  # e.g., "BED001"
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)  # BED, WHEELCHAIR, OXYGEN, ACCESSORY
    description = Column(Text, nullable=True)
    is_serialized = Column(Boolean, nullable=False, default=False)  # Requires UID scanning
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    items = relationship("Item", back_populates="sku")
    aliases = relationship("SKUAlias", back_populates="sku")
    lorry_stocks = relationship("LorryStock", back_populates="sku")