import enum
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Date, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class AttendanceStatus(enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"
    HALF_DAY = "Half Day"
    ON_LEAVE = "On Leave"

class AttendanceReport(Base):
    __tablename__ = "attendance_reports"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    total_hours = Column(Float, default=0.0)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.ABSENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="attendance_reports")
