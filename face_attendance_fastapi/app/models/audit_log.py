import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.sql import func
from app.db.base import Base


class AuditAction(enum.Enum):
    # Original actions
    USER_CREATED = "User Created"
    USER_UPDATED = "User Updated"
    FACE_ENROLLED = "Face Enrolled"
    ATTENDANCE_MARKED = "Attendance Marked"
    REPORT_GENERATED = "Report Generated"
    LOGIN = "Login"
    LOGOUT = "Logout"
    # New actions
    RESOLVE_DISPUTE = "Resolve Dispute"
    APPROVE_LEAVE = "Approve Leave"
    REJECT_LEAVE = "Reject Leave"
    USER_DELETED = "User Deleted"
    SUBJECT_CREATED = "Subject Created"
    SUBJECT_DELETED = "Subject Deleted"
    SESSION_ACTIVATED = "Session Activated"
    ATTENDANCE_LOCKED = "Attendance Locked"
    ADMIN_OVERRIDE = "Admin Override"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(Enum(AuditAction), nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String, nullable=True)          # kept even if user is deleted
    target_user_id = Column(Integer, nullable=True)
    target_type = Column(String, nullable=True)          # "SubjectAttendance", "LeaveRequest" etc.
    target_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)              # JSON string of before-state
    new_value = Column(Text, nullable=True)              # JSON string of after-state
    description = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
