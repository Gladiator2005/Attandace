from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.models.academic_session import AcademicSession
from sqlalchemy import select
from app.crud.audit import log_action
from app.models.audit_log import AuditAction


router = APIRouter()


class SessionCreate(BaseModel):
    name: str  # e.g. "2025-26 Odd Sem"
    start_date: str  # YYYY-MM-DD
    end_date: str


@router.post("/")
async def create_session(
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    session = AcademicSession(
        name=data.name,
        start_date=date.fromisoformat(data.start_date),
        end_date=date.fromisoformat(data.end_date),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": session.id, "message": f"Session '{data.name}' created"}


@router.get("/")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicSession).order_by(AcademicSession.start_date.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id, "name": s.name,
            "start_date": str(s.start_date), "end_date": str(s.end_date),
            "is_active": s.is_active,
        }
        for s in sessions
    ]


@router.post("/{session_id}/activate")
async def activate_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Deactivate all
    all_sessions = await db.execute(select(AcademicSession))
    for s in all_sessions.scalars().all():
        s.is_active = False
    # Activate selected
    result = await db.execute(select(AcademicSession).where(AcademicSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_active = True
    
    await log_action(
        db, AuditAction.SESSION_ACTIVATED, actor=current_user,
        target_type="AcademicSession", target_id=session.id,
        new_value={"is_active": True, "name": session.name},
        description=f"Admin {current_user.email} activated session '{session.name}'"
    )
    
    await db.commit()
    return {"message": f"Session '{session.name}' is now active"}


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    result = await db.execute(select(AcademicSession).where(AcademicSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted"}
