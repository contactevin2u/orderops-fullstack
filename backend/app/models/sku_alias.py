from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base


class SKUAlias(Base):
    __tablename__ = "sku_alias"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_id = Column(Integer, ForeignKey("sku.id"), nullable=False)
    alias_text = Column(String, nullable=False)
    weight = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('sku_id', 'alias_text', name='uq_sku_alias_sku_text'),
    )
    
    # Relationships
    sku = relationship("SKU", back_populates="aliases")