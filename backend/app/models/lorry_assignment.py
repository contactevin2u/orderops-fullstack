from datetime import datetime, date
from sqlalchemy import (
    BigInteger,
    DateTime,
    Date,
    String,
    ForeignKey,
    Boolean,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LorryAssignment(Base):
    """Daily lorry assignments to drivers"""
    __tablename__ = "lorry_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    lorry_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # Lorry identifier (e.g., "LRY001")
    assignment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Shift integration
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("driver_shifts.id"), nullable=True, index=True)
    
    # Stock verification status
    stock_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stock_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Assignment status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSIGNED")  # ASSIGNED, ACTIVE, COMPLETED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Admin assignment tracking
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    driver = relationship("Driver", back_populates="lorry_assignments")
    shift = relationship("DriverShift", back_populates="lorry_assignment")
    assigned_by_user = relationship("User")
    stock_verifications = relationship("LorryStockVerification", back_populates="assignment")

    def __repr__(self):
        return f"<LorryAssignment(driver_id={self.driver_id}, lorry_id={self.lorry_id}, date={self.assignment_date})>"


class LorryStockVerification(Base):
    """Record of lorry stock verification scans during clock-in"""
    __tablename__ = "lorry_stock_verifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("lorry_assignments.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    lorry_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Verification details
    verification_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scanned_uids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of scanned UIDs
    total_scanned: Mapped[int] = mapped_column(nullable=False, default=0)
    
    # Expected vs actual comparison
    expected_uids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of expected UIDs
    total_expected: Mapped[int | None] = mapped_column(nullable=True, default=0)
    variance_count: Mapped[int | None] = mapped_column(nullable=True, default=0)
    
    # Missing and unexpected UIDs
    missing_uids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    unexpected_uids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="VERIFIED")  # VERIFIED, VARIANCE_DETECTED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    assignment = relationship("LorryAssignment", back_populates="stock_verifications")
    driver = relationship("Driver")

    def __repr__(self):
        return f"<LorryStockVerification(lorry_id={self.lorry_id}, date={self.verification_date}, variance={self.variance_count})>"


class DriverHold(Base):
    """Driver holds for accountability and investigation"""
    __tablename__ = "driver_holds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    
    # Hold details
    reason: Mapped[str] = mapped_column(String(100), nullable=False)  # STOCK_VARIANCE, INVESTIGATION, etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Related records
    related_assignment_id: Mapped[int | None] = mapped_column(ForeignKey("lorry_assignments.id"), nullable=True)
    related_verification_id: Mapped[int | None] = mapped_column(ForeignKey("lorry_stock_verifications.id"), nullable=True)
    
    # Hold status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, RESOLVED
    
    # Admin actions
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    driver = relationship("Driver", back_populates="holds")
    created_by_user = relationship("User", foreign_keys=[created_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    related_assignment = relationship("LorryAssignment")
    related_verification = relationship("LorryStockVerification")

    @property
    def is_active(self) -> bool:
        """Check if hold is currently active"""
        return self.status == "ACTIVE" and self.resolved_at is None

    def __repr__(self):
        return f"<DriverHold(driver_id={self.driver_id}, reason={self.reason}, status={self.status})>"