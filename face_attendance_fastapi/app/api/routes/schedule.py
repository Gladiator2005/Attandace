from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import time as dt_time
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.schedule import (
    create_schedule, get_all_schedules, get_schedules_by_subject,
    delete_schedule, get_current_subject_for_student, get_today_schedule_for_student,
    check_schedule_conflict,
)

router = APIRouter()


class ScheduleCreate(BaseModel):
    subject_id: int
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str   # "HH:MM"
    end_time: str     # "HH:MM"
    room: Optional[str] = None


@router.post("/")
async def create_new_schedule(
    data: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    if data.day_of_week < 0 or data.day_of_week > 6:
        raise HTTPException(status_code=400, detail="day_of_week must be 0-6")
    start = dt_time.fromisoformat(data.start_time)
    end = dt_time.fromisoformat(data.end_time)
    if start >= end:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    # Check for timetable conflicts
    conflict = await check_schedule_conflict(db, data.subject_id, data.day_of_week, start, end, data.room)
    if conflict:
        raise HTTPException(status_code=409, detail=conflict)
    sched = await create_schedule(db, data.subject_id, data.day_of_week, start, end, data.room)
    return {"id": sched.id, "message": "Schedule created"}


@router.get("/")
async def list_schedules(
    subject_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if subject_id:
        schedules = await get_schedules_by_subject(db, subject_id)
    else:
        schedules = await get_all_schedules(db)
    return [
        {
            "id": s.id, "subject_id": s.subject_id,
            "subject_code": s.subject.code if s.subject else "",
            "subject_name": s.subject.name if s.subject else "",
            "day_of_week": s.day_of_week, "day_name": s.day_name,
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "room": s.room,
        }
        for s in schedules
    ]


@router.delete("/{schedule_id}")
async def delete_existing_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    deleted = await delete_schedule(db, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted"}


@router.get("/my-current")
async def get_my_current_class(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student: get what class they should be in right now."""
    from datetime import datetime
    now = datetime.now()
    current_day = now.weekday()  # 0=Monday
    current_time = now.time()
    subject = await get_current_subject_for_student(db, current_user.id, current_day, current_time)
    if not subject:
        return {"current_subject": None, "message": "No class scheduled right now"}
    return {
        "current_subject": {
            "id": subject.id, "code": subject.code, "name": subject.name,
        },
        "message": f"You should be in {subject.code} – {subject.name}",
    }


@router.get("/my-today")
async def get_my_today_classes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student: get all classes for today."""
    from datetime import datetime
    current_day = datetime.now().weekday()
    schedules = await get_today_schedule_for_student(db, current_user.id, current_day)
    return [
        {
            "subject_id": s.subject_id,
            "subject_code": s.subject.code if s.subject else "",
            "subject_name": s.subject.name if s.subject else "",
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "room": s.room,
        }
        for s in schedules
    ]
