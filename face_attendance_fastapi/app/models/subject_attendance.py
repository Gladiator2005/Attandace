import enum
from sqlalchemy import Column, Integer, ForeignKey, Date, Enum, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class AttendanceStatus(enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"


class FinalStatus(enum.Enum):
    PRESENT = "Present"       # Both face + faculty verified
    DISPUTED = "Disputed"     # Only one source verified
    ABSENT = "Absent"         # Neither verified
    PENDING = "Pending"       # Waiting for reconciliation


class SubjectAttendance(Base):
    __tablename__ = "subject_attendance"
    __table_args__ = (
        UniqueConstraint('student_id', 'subject_id', 'date', name='uq_student_subject_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)

    # Dual verification fields
    face_verified = Column(Boolean, default=False)     # student scanned face
    faculty_marked = Column(Boolean, default=False)    # faculty marked in roll call
    final_status = Column(Enum(FinalStatus), default=FinalStatus.PENDING)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # admin who resolved dispute
    is_locked = Column(Boolean, default=False)  # locked after grace period

    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("User", foreign_keys=[student_id], backref="subject_attendance_records")
    subject = relationship("Subject", back_populates="attendance_records")
    marker = relationship("User", foreign_keys=[marked_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
