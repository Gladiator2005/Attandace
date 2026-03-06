from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.leave import (
    create_leave_request, get_pending_leaves, get_student_leaves,
    approve_leave, reject_leave,
)

router = APIRouter()


class LeaveCreateRequest(BaseModel):
    subject_id: int
    leave_date: str  # YYYY-MM-DD
    leave_type: str = "Personal"  # Medical / Personal / On Duty
    reason: str


@router.post("/")
async def submit_leave(
    data: LeaveCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student submits a leave request."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit leave requests")
    try:
        leave_date = date.fromisoformat(data.leave_date)
        leave = await create_leave_request(
            db, current_user.id, data.subject_id, leave_date, data.leave_type, data.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": leave.id, "message": "Leave request submitted"}


@router.get("/my-requests")
async def my_leave_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student views their leave requests."""
    leaves = await get_student_leaves(db, current_user.id)
    return [
        {
            "id": l.id,
            "subject_code": l.subject.code if l.subject else "",
            "subject_name": l.subject.name if l.subject else "",
            "leave_date": str(l.leave_date),
            "leave_type": l.leave_type.value,
            "reason": l.reason,
            "status": l.status.value,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leaves
    ]


@router.get("/pending")
async def pending_leave_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Faculty/admin views pending leave requests."""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Not allowed")
    faculty_id = current_user.id if current_user.role == UserRole.FACULTY else None
    leaves = await get_pending_leaves(db, faculty_id)
    return [
        {
            "id": l.id,
            "student_id": l.student_id,
            "student_name": l.student.full_name if l.student else "Unknown",
            "enrollment_no": l.student.employee_id if l.student else "",
            "subject_code": l.subject.code if l.subject else "",
            "subject_name": l.subject.name if l.subject else "",
            "leave_date": str(l.leave_date),
            "leave_type": l.leave_type.value,
            "reason": l.reason,
            "status": l.status.value,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leaves
    ]


@router.post("/{leave_id}/approve")
async def approve_leave_request(
    leave_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Not allowed")
    try:
        leave = await approve_leave(db, leave_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return {"message": "Leave approved. Attendance adjusted to Present."}


@router.post("/{leave_id}/reject")
async def reject_leave_request(
    leave_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Not allowed")
    try:
        leave = await reject_leave(db, leave_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return {"message": "Leave rejected."}
