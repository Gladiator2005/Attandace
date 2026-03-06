import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class EntryType(enum.Enum):
    CHECK_IN = "Check In"
    CHECK_OUT = "Check Out"

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_type = Column(Enum(EntryType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=True)
    is_late = Column(Boolean, default=False)
    user = relationship("User", back_populates="attendance_records")
