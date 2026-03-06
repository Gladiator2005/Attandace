from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuditLogCreate(BaseModel):
    action: str
    performed_by: Optional[int] = None
    target_user_id: Optional[int] = None
    description: Optional[str] = None

class AuditLogResponse(BaseModel):
    id: int
    action: str
    performed_by: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
