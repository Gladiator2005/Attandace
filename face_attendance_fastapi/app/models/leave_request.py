import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class LeaveType(enum.Enum):
    MEDICAL = "Medical"
    PERSONAL = "Personal"
    OD = "On Duty"  # Official Duty / event attendance


class LeaveStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    leave_date = Column(Date, nullable=False)
    leave_type = Column(Enum(LeaveType), default=LeaveType.PERSONAL)
    reason = Column(Text, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("User", foreign_keys=[student_id], backref="leave_requests")
    subject = relationship("Subject", backref="leave_requests")
    approver = relationship("User", foreign_keys=[approved_by])
