from datetime import time, date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.class_schedule import ClassSchedule
from app.models.subject_enrollment import SubjectEnrollment
from app.models.subject import Subject


async def check_schedule_conflict(db: AsyncSession, subject_id: int, day_of_week: int,
                                   start_time: time, end_time: time, room: str = None,
                                   exclude_id: int = None) -> Optional[str]:
    """Check for timetable conflicts. Returns error message or None."""
    # 1. Same subject cannot have overlapping slots on same day
    query = select(ClassSchedule).where(
        ClassSchedule.subject_id == subject_id,
        ClassSchedule.day_of_week == day_of_week,
        ClassSchedule.start_time < end_time,
        ClassSchedule.end_time > start_time,
    )
    if exclude_id:
        query = query.where(ClassSchedule.id != exclude_id)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        return "This subject already has a class scheduled during this time slot on this day."

    # 2. Same room cannot be double-booked on same day
    if room:
        query2 = select(ClassSchedule).options(selectinload(ClassSchedule.subject)).where(
            ClassSchedule.room == room,
            ClassSchedule.day_of_week == day_of_week,
            ClassSchedule.start_time < end_time,
            ClassSchedule.end_time > start_time,
        )
        if exclude_id:
            query2 = query2.where(ClassSchedule.id != exclude_id)
        result2 = await db.execute(query2)
        conflict = result2.scalar_one_or_none()
        if conflict:
            sub_code = conflict.subject.code if conflict.subject else "Unknown"
            return f"Room '{room}' is already booked for {sub_code} at this time."

    return None


async def create_schedule(db: AsyncSession, subject_id: int, day_of_week: int,
                          start_time: time, end_time: time, room: str = None) -> ClassSchedule:
    schedule = ClassSchedule(
        subject_id=subject_id, day_of_week=day_of_week,
        start_time=start_time, end_time=end_time, room=room,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_schedules_by_subject(db: AsyncSession, subject_id: int) -> List[ClassSchedule]:
    result = await db.execute(
        select(ClassSchedule).options(selectinload(ClassSchedule.subject))
        .where(ClassSchedule.subject_id == subject_id)
        .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
    )
    return result.scalars().all()


async def get_all_schedules(db: AsyncSession) -> List[ClassSchedule]:
    result = await db.execute(
        select(ClassSchedule).options(selectinload(ClassSchedule.subject))
        .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
    )
    return result.scalars().all()


async def get_schedule_by_id(db: AsyncSession, schedule_id: int) -> Optional[ClassSchedule]:
    result = await db.execute(
        select(ClassSchedule).options(selectinload(ClassSchedule.subject))
        .where(ClassSchedule.id == schedule_id)
    )
    return result.scalar_one_or_none()


async def delete_schedule(db: AsyncSession, schedule_id: int) -> bool:
    sched = await get_schedule_by_id(db, schedule_id)
    if not sched:
        return False
    await db.delete(sched)
    await db.commit()
    return True


async def get_current_subject_for_student(db: AsyncSession, student_id: int, current_day: int,
                                          current_time: time) -> Optional[Subject]:
    """Find what subject a student should be in right now based on schedule."""
    enrolled = await db.execute(
        select(SubjectEnrollment.subject_id).where(SubjectEnrollment.student_id == student_id)
    )
    enrolled_ids = [row[0] for row in enrolled.all()]
    if not enrolled_ids:
        return None

    # Use exclusive end time to avoid back-to-back overlap
    result = await db.execute(
        select(ClassSchedule).options(selectinload(ClassSchedule.subject))
        .where(
            ClassSchedule.subject_id.in_(enrolled_ids),
            ClassSchedule.day_of_week == current_day,
            ClassSchedule.start_time <= current_time,
            ClassSchedule.end_time > current_time,  # exclusive end
        )
        .order_by(ClassSchedule.start_time)
    )
    schedule = result.scalar_one_or_none()
    return schedule.subject if schedule else None


async def get_today_schedule_for_student(db: AsyncSession, student_id: int,
                                         current_day: int) -> List[ClassSchedule]:
    """Get all classes for a student today."""
    enrolled = await db.execute(
        select(SubjectEnrollment.subject_id).where(SubjectEnrollment.student_id == student_id)
    )
    enrolled_ids = [row[0] for row in enrolled.all()]
    if not enrolled_ids:
        return []

    result = await db.execute(
        select(ClassSchedule).options(selectinload(ClassSchedule.subject))
        .where(
            ClassSchedule.subject_id.in_(enrolled_ids),
            ClassSchedule.day_of_week == current_day,
        )
        .order_by(ClassSchedule.start_time)
    )
    return result.scalars().all()
