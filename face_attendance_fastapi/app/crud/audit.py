import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User


async def log_action(
    db: AsyncSession,
    action: AuditAction,
    actor: Optional[User] = None,
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Create an audit log entry (flush without committing — caller commits)."""
    entry = AuditLog(
        action=action,
        performed_by=actor.id if actor else actor_id,
        actor_email=actor.email if actor else actor_email,
        target_type=target_type,
        target_id=target_id,
        target_user_id=target_user_id,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
        description=description,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
) -> tuple:
    """Returns (items, total) with optional filters."""
    from sqlalchemy import func as sqlfunc
    query = select(AuditLog)
    count_q = select(sqlfunc.count(AuditLog.id))
    if actor_id:
        query = query.where(AuditLog.performed_by == actor_id)
        count_q = count_q.where(AuditLog.performed_by == actor_id)
    if action:
        try:
            aen = AuditAction(action)
            query = query.where(AuditLog.action == aen)
            count_q = count_q.where(AuditLog.action == aen)
        except ValueError:
            pass
    total = (await db.execute(count_q)).scalar() or 0
    items = (await db.execute(query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit))).scalars().all()
    return items, total
