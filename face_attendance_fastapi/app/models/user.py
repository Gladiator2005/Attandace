import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class UserRole(enum.Enum):
    ADMIN = "Admin"
    FACULTY = "Faculty"
    STUDENT = "Student"
    MENTOR = "Mentor"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, nullable=False, index=True)  # enrollment_no for students
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    department = Column(String, nullable=True)
    
    # Granular cohort assignment (For Students & Mentors)
    program = Column(String, nullable=True)         # e.g., "B.Tech", "BCA"
    major = Column(String, nullable=True)           # e.g., "Computer Science"
    specialization = Column(String, nullable=True)  # e.g., "AI/ML", "Data Science"
    section = Column(String, nullable=True)         # e.g., "A", "2024-B"
    
    semester = Column(Integer, nullable=True)  # for students
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)  # soft-delete: user stays in DB
    has_face_data = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    face_data = relationship("FaceData", back_populates="user", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="user", cascade="all, delete-orphan")
    attendance_reports = relationship("AttendanceReport", back_populates="user", cascade="all, delete-orphan")

    # College ERP relationships
    enrolled_subjects = relationship("SubjectEnrollment", back_populates="student", cascade="all, delete-orphan", foreign_keys="SubjectEnrollment.student_id")
    taught_subjects = relationship("Subject", back_populates="faculty", foreign_keys="Subject.faculty_id")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
