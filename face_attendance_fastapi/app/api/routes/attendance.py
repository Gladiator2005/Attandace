from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, time
import json
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User
from app.models.attendance import EntryType
from app.models.attendance_report import AttendanceStatus
from app.crud.attendance import create_attendance, get_today_attendance
from app.crud.face_data import get_all_face_data
from app.crud.report import get_or_create_report
from app.services.face_recognition_service import face_service

router = APIRouter()

@router.post("/mark")
async def mark_attendance(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    contents = await file.read()
    encoding, quality = face_service.extract_encoding(contents)
    if encoding is None:
        raise HTTPException(status_code=400, detail="No face detected")
    all_faces = await get_all_face_data(db)
    if not all_faces:
        raise HTTPException(status_code=400, detail="No face data in system. Please enroll first.")
    known = [(f.user_id, f.encoding) for f in all_faces]
    user_id, confidence = face_service.match_face(encoding, known)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Face not recognized")
    from app.crud.user import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    today_records = await get_today_attendance(db, user_id)
    if not today_records:
        entry_type = EntryType.CHECK_IN
    else:
        last = today_records[0]
        entry_type = EntryType.CHECK_OUT if last.entry_type == EntryType.CHECK_IN else EntryType.CHECK_IN
    now = datetime.now()
    is_late = entry_type == EntryType.CHECK_IN and now.time() > time(9, 0)
    record = await create_attendance(db, user_id, entry_type, confidence, is_late=is_late)
    report = await get_or_create_report(db, user_id, now.date())
    if entry_type == EntryType.CHECK_IN:
        report.check_in_time = now
        report.status = AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT
    else:
        report.check_out_time = now
        if report.check_in_time:
            delta = now - report.check_in_time
            report.total_hours = round(delta.total_seconds() / 3600, 2)
    await db.commit()
    return {"user_name": user.full_name, "entry_type": entry_type.value, "confidence": confidence, "timestamp": now.isoformat(), "is_late": is_late}

@router.get("/today")
async def today_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    records = await get_today_attendance(db, current_user.id)
    if not records:
        return {"status": "absent", "records": []}
    last = records[0]
    status = "late" if last.is_late else "present"
    return {"status": status, "records": [{"entry_type": r.entry_type.value, "time": r.timestamp.strftime("%H:%M:%S")} for r in records]}
