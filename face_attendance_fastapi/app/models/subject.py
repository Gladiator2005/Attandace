from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # e.g. "CS101"
    name = Column(String, nullable=False)  # e.g. "Data Structures"
    department = Column(String, nullable=True)
    semester = Column(Integer, nullable=True)
    total_classes = Column(Integer, default=40)  # total scheduled classes in semester
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id"), nullable=True)
    attendance_threshold = Column(Float, default=75.0)  # configurable per-subject (e.g. 75%, 80%)
    is_deleted = Column(Boolean, default=False)  # soft delete — subject stays in DB
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    faculty = relationship("User", back_populates="taught_subjects", foreign_keys=[faculty_id])
    session = relationship("AcademicSession", back_populates="subjects")
    enrollments = relationship("SubjectEnrollment", back_populates="subject", cascade="all, delete-orphan")
    attendance_records = relationship("SubjectAttendance", back_populates="subject", cascade="all, delete-orphan")
