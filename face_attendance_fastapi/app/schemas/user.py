from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    password: str
    phone: Optional[str] = None
    department: Optional[str] = None
    program: Optional[str] = None
    major: Optional[str] = None
    specialization: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[int] = None
    role: str = "Student"


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    program: Optional[str] = None
    major: Optional[str] = None
    specialization: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[int] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    program: Optional[str] = None
    major: Optional[str] = None
    specialization: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[int] = None
    role: str
    is_active: bool
    has_face_data: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
