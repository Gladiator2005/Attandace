from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.attendance_notification import AttendanceNotification, NotificationType


async def create_notification(db: AsyncSession, user_id: int, subject_id: int,
                               ntype: NotificationType, message: str,
                               attendance_id: int = None) -> AttendanceNotification:
    notif = AttendanceNotification(
        user_id=user_id, subject_id=subject_id,
        subject_attendance_id=attendance_id,
        type=ntype, message=message,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def get_notifications(db: AsyncSession, user_id: int, unread_only: bool = False,
                             limit: int = 50) -> List[AttendanceNotification]:
    query = select(AttendanceNotification).where(
        AttendanceNotification.user_id == user_id
    )
    if unread_only:
        query = query.where(AttendanceNotification.is_read == False)
    query = query.order_by(AttendanceNotification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(AttendanceNotification.id)).where(
            AttendanceNotification.user_id == user_id,
            AttendanceNotification.is_read == False,
        )
    )
    return result.scalar() or 0


async def mark_as_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(AttendanceNotification).where(
            AttendanceNotification.id == notification_id,
            AttendanceNotification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.is_read = True
    await db.commit()
    return True


async def mark_all_read(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(AttendanceNotification).where(
            AttendanceNotification.user_id == user_id,
            AttendanceNotification.is_read == False,
        )
    )
    for notif in result.scalars().all():
        notif.is_read = True
    await db.commit()
