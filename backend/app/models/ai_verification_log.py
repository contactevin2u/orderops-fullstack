"""AI Verification Log Model - Track AI analysis calls for rate limiting and auditing"""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, Text, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AIVerificationLog(Base):
    __tablename__ = "ai_verification_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Analysis results
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "cash", "bank_transfer", "unknown"
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    cash_collection_required: Mapped[bool] = mapped_column(default=False)
    
    # Full analysis details
    analysis_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_notes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    # Metadata
    success: Mapped[bool] = mapped_column(default=False)
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    trip = relationship("Trip", backref="ai_verification_logs")
    user = relationship("User", backref="ai_verification_logs")