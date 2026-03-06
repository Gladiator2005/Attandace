import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class NotificationType(enum.Enum):
    FACE_ONLY = "Face Only"         # Face scan but no faculty mark
    FACULTY_ONLY = "Faculty Only"   # Faculty marked but no face scan
    ABSENT = "Absent"               # Neither — final absent
    RESOLVED = "Resolved"           # Admin resolved a dispute


class AttendanceNotification(Base):
    __tablename__ = "attendance_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_attendance_id = Column(Integer, ForeignKey("subject_attendance.id", ondelete="CASCADE"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")
    subject = relationship("Subject")
