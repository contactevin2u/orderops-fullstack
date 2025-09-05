from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Organization(Base):
    """Enterprise organization/tenant model for multi-tenancy"""
    __tablename__ = "organizations"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(20), default="STARTER")  # STARTER|PROFESSIONAL|ENTERPRISE
    monthly_order_limit: Mapped[int] = mapped_column(default=500)
    driver_limit: Mapped[int] = mapped_column(default=5)
    
    # Enterprise features flags
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    api_access_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    white_label_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_integrations_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Contact info
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Billing
    monthly_revenue: Mapped[int] = mapped_column(default=2500)  # In cents
    billing_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Metadata
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON settings
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships (to be added to other models)
    # users = relationship("User", back_populates="organization")
    # customers = relationship("Customer", back_populates="organization")
    # orders = relationship("Order", back_populates="organization")