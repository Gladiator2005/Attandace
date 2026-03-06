from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class SubjectCreate(BaseModel):
    code: str
    name: str
    department: Optional[str] = None
    semester: Optional[int] = None
    total_classes: int = 40
    faculty_id: Optional[int] = None
    session_id: Optional[int] = None
    attendance_threshold: float = 75.0


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    total_classes: Optional[int] = None
    faculty_id: Optional[int] = None
    session_id: Optional[int] = None
    attendance_threshold: Optional[float] = None


class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    department: Optional[str] = None
    semester: Optional[int] = None
    total_classes: int
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    enrolled_count: int = 0
    attendance_threshold: float = 75.0
    session_id: Optional[int] = None

    class Config:
        from_attributes = True


class EnrollStudentsRequest(BaseModel):
    student_ids: List[int]


class MarkAttendanceEntry(BaseModel):
    student_id: int
    status: str = "Present"  # Present / Absent / Late


class MarkAttendanceRequest(BaseModel):
    date: str  # YYYY-MM-DD
    entries: List[MarkAttendanceEntry]


class SubjectAttendanceResponse(BaseModel):
    student_id: int
    student_name: str
    enrollment_no: str
    date: str
    status: str

    class Config:
        from_attributes = True


class StudentThresholdStatus(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    total_scheduled: int
    classes_conducted: int
    classes_attended: int
    percentage: float
    threshold: float = 75.0
    above_threshold: bool
    days_needed: int  # more classes needed to reach 75%
    days_off: int  # classes they can skip and stay ≥75%


class StudentThresholdOverview(BaseModel):
    student_id: int
    student_name: str
    enrollment_no: str
    department: Optional[str] = None
    subject_code: str
    subject_name: str
    percentage: float
    above_threshold: bool
    classes_attended: int
    classes_conducted: int
