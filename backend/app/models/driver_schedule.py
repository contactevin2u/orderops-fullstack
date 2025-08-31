"""Driver work schedule model for managing daily rosters"""

from datetime import date, datetime
from sqlalchemy import Date, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DriverSchedule(Base):
    """Daily work schedule for drivers"""
    __tablename__ = "driver_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shift_type: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL_DAY")  # FULL_DAY, MORNING, EVENING
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCHEDULED")  # SCHEDULED, CONFIRMED, CALLED_SICK, NO_SHOW
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    driver = relationship("Driver", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<DriverSchedule driver_id={self.driver_id} date={self.schedule_date} status={self.status}>"


class DriverAvailabilityPattern(Base):
    """Weekly availability patterns for drivers (recurring schedules)"""
    __tablename__ = "driver_availability_patterns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    
    # Weekly pattern (0=Monday, 6=Sunday)
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    thursday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    saturday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Pattern metadata
    pattern_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "Team A", "Weekdays Only"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # None means ongoing
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    driver = relationship("Driver", back_populates="availability_patterns")

    def __repr__(self) -> str:
        return f"<DriverAvailabilityPattern driver_id={self.driver_id} pattern={self.pattern_name}>"

    def get_days_string(self) -> str:
        """Get a readable string of scheduled days"""
        days = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_values = [self.monday, self.tuesday, self.wednesday, self.thursday, 
                     self.friday, self.saturday, self.sunday]
        
        for i, is_scheduled in enumerate(day_values):
            if is_scheduled:
                days.append(day_names[i])
        
        return ", ".join(days) if days else "No days scheduled"

    def is_scheduled_for_day(self, weekday: int) -> bool:
        """Check if driver is scheduled for given weekday (0=Monday, 6=Sunday)"""
        day_mapping = [
            self.monday, self.tuesday, self.wednesday, self.thursday,
            self.friday, self.saturday, self.sunday
        ]
        return day_mapping[weekday] if 0 <= weekday <= 6 else False