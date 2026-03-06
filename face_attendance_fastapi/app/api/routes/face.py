from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import json
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User
from app.crud.face_data import create_face_data, get_face_data_by_user
from app.services.face_recognition_service import face_service

router = APIRouter()

@router.post("/upload")
async def upload_face(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG images are allowed")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    encoding, quality = face_service.extract_encoding(contents)
    if encoding is None:
        raise HTTPException(status_code=400, detail="No face detected in image. Please try again with a clear photo.")
    encoding_str = json.dumps(encoding)
    face_data = await create_face_data(db, current_user.id, encoding_str, face_quality=quality)
    current_user.has_face_data = True
    await db.commit()
    return {"message": "Face enrolled successfully", "face_quality": round(quality, 1), "id": face_data.id}

@router.get("/status")
async def face_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    faces = await get_face_data_by_user(db, current_user.id)
    return {"has_face_data": len(faces) > 0, "count": len(faces)}
