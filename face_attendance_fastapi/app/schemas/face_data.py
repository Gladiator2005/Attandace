from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FaceDataCreate(BaseModel):
    user_id: int
    encoding: str
    image_path: Optional[str] = None
    face_quality: float = 0.0

class FaceDataResponse(BaseModel):
    id: int
    user_id: int
    face_quality: float
    is_verified: bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
