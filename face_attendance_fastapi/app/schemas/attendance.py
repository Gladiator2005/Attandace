from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AttendanceCreate(BaseModel):
    user_id: int
    entry_type: str
    confidence_score: float = 0.0
    image_url: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    entry_type: str
    timestamp: datetime
    confidence_score: float
    is_verified: bool
    is_late: bool
    date: Optional[str] = None
    time: Optional[str] = None
    class Config:
        from_attributes = True

class AttendanceFilter(BaseModel):
    user_id: Optional[int] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    entry_type: Optional[str] = None
