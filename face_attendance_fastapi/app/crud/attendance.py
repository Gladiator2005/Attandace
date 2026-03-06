from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, datetime
from app.models.attendance import Attendance, EntryType
from app.models.user import User

async def create_attendance(db: AsyncSession, user_id: int, entry_type: EntryType, confidence_score: float, image_url: str = None, is_late: bool = False):
    record = Attendance(user_id=user_id, entry_type=entry_type, confidence_score=confidence_score, image_url=image_url, is_late=is_late)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record

async def get_today_attendance(db: AsyncSession, user_id: int):
    today = date.today()
    result = await db.execute(select(Attendance).where(and_(Attendance.user_id == user_id, func.date(Attendance.timestamp) == today)).order_by(Attendance.timestamp.desc()))
    return result.scalars().all()

async def get_attendance_records(db: AsyncSession, user_id: int = None, from_date: str = None, to_date: str = None, skip: int = 0, limit: int = 20):
    query = select(Attendance)
    if user_id:
        query = query.where(Attendance.user_id == user_id)
    if from_date:
        query = query.where(func.date(Attendance.timestamp) >= from_date)
    if to_date:
        query = query.where(func.date(Attendance.timestamp) <= to_date)
    query = query.order_by(Attendance.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def count_present_today(db: AsyncSession):
    today = date.today()
    result = await db.execute(select(func.count(func.distinct(Attendance.user_id))).where(func.date(Attendance.timestamp) == today))
    return result.scalar() or 0
