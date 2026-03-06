from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class AttendanceReportResponse(BaseModel):
    id: int
    user_id: int
    date: date
    status: str
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    total_hours: float
    class Config:
        from_attributes = True

class ReportFilter(BaseModel):
    user_id: Optional[int] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    status: Optional[str] = None
