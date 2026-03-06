from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.subject_attendance import get_student_threshold_status, get_all_students_threshold

router = APIRouter()


@router.get("/my-status")
async def my_threshold_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student: get threshold status for all enrolled subjects."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="This endpoint is for students only")
    subjects = await get_student_threshold_status(db, current_user.id)
    return {"student_id": current_user.id, "student_name": current_user.full_name, "subjects": subjects}


@router.get("/students")
async def students_threshold(
    subject_id: int = None,
    filter: str = None,  # "below" or "above"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Faculty/Admin: list students with threshold status."""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    rows = await get_all_students_threshold(db, subject_id)
    if filter == "below":
        rows = [r for r in rows if not r["above_threshold"]]
    elif filter == "above":
        rows = [r for r in rows if r["above_threshold"]]
    return {"students": rows, "threshold": 75.0}
