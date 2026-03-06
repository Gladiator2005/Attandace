from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.audit import get_audit_logs
from fastapi import HTTPException

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor_id: int = None,
    action: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    items, total = await get_audit_logs(db, skip=skip, limit=limit,
                                        actor_id=actor_id, action=action)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": a.id,
                "action": a.action.value,
                "actor_email": a.actor_email,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "description": a.description,
                "ip_address": a.ip_address,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
    }
