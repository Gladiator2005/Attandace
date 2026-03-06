from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User
from app.crud.notifications import get_notifications, get_unread_count, mark_as_read, mark_all_read

router = APIRouter()


@router.get("/")
async def list_notifications(
    unread: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifs = await get_notifications(db, current_user.id, unread_only=unread)
    return {
        "notifications": [
            {
                "id": n.id, "type": n.type.value, "message": n.message,
                "subject_id": n.subject_id,
                "attendance_id": n.subject_attendance_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
        "unread_count": await get_unread_count(db, current_user.id),
    }


@router.get("/count")
async def notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await mark_as_read(db, notification_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await mark_all_read(db, current_user.id)
    return {"message": "All marked as read"}
