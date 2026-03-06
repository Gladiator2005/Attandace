from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.user import count_users, get_users
from app.crud.attendance import count_present_today
from app.services.dispute_resolution_service import resolve_disputed_record

router = APIRouter()


class AdminResolveRequest(BaseModel):
    final_status: str  # "Present" or "Absent"
    notes: str | None = None

@router.get("/stats")
async def admin_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Access denied")
    total = await count_users(db)
    present = await count_present_today(db)
    absent = total - present
    rate = round((present / total) * 100) if total > 0 else 0
    return {"total_employees": total, "present_today": present, "absent_today": absent, "attendance_rate": rate}

@router.post("/attendance/{record_id}/resolve")
async def admin_resolve_attendance(
    record_id: int,
    data: AdminResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_disputed_record(
        db=db,
        record_id=record_id,
        final_status=data.final_status,
        actor=current_user,
        notes=data.notes,
    )
    return {
        "message": "Attendance record resolved successfully",
        "record_id": resolved.id,
        "final_status": resolved.final_status.value,
    }

@router.get("/departments")
async def department_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(select(User.department, func.count(User.id)).where(User.is_active == True).group_by(User.department))
    departments = []
    for dept, count in result.all():
        departments.append({"department": dept or "Unassigned", "total_employees": count, "present_today": 0, "attendance_rate": 0})
    return {"departments": departments}

@router.get("/users")
async def admin_users(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await get_users(db)
    return [{"id": u.id, "employee_id": u.employee_id, "name": u.full_name, "email": u.email, "role": u.role.value, "department": u.department, "is_active": u.is_active, "has_face_data": u.has_face_data} for u in users]
