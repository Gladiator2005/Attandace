from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.models.subject_attendance import SubjectAttendance, FinalStatus
from app.models.subject_enrollment import SubjectEnrollment

router = APIRouter()

def check_mentor_access(current_user: User):
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=403, detail="Mentor access required")

@router.get("/mentees")
async def get_my_mentees(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all students belonging to this mentor's specific cohort."""
    check_mentor_access(current_user)
    
    # Match students on all 4 cohort fields that the mentor is assigned to
    query = select(User).where(
        User.role == UserRole.STUDENT,
        User.is_active == True,
        User.program == current_user.program,
        User.major == current_user.major,
        User.specialization == current_user.specialization,
        User.section == current_user.section
    ).order_by(User.first_name)
    
    result = await db.execute(query)
    students = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "enrollment_no": s.employee_id,
            "name": s.full_name,
            "program": s.program,
            "major": s.major,
            "specialization": s.specialization,
            "section": s.section
        }
        for s in students
    ]

@router.get("/disputes")
async def get_my_mentee_disputes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending attendance disputes ONLY for this mentor's assigned students."""
    check_mentor_access(current_user)
    
    query = select(SubjectAttendance).options(
        selectinload(SubjectAttendance.student),
        selectinload(SubjectAttendance.subject)
    ).join(User, SubjectAttendance.student_id == User.id).where(
        SubjectAttendance.final_status == FinalStatus.DISPUTED,
        User.program == current_user.program,
        User.major == current_user.major,
        User.specialization == current_user.specialization,
        User.section == current_user.section
    ).order_by(SubjectAttendance.date.desc())
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return [
        {
            "id": r.id, 
            "student_id": r.student_id,
            "student_name": r.student.full_name if r.student else "",
            "enrollment_no": r.student.employee_id if r.student else "",
            "subject_id": r.subject_id,
            "subject_code": r.subject.code if r.subject else "",
            "subject_name": r.subject.name if r.subject else "",
            "date": r.date.isoformat(),
            "face_verified": r.face_verified,
            "faculty_marked": r.faculty_marked,
            "final_status": r.final_status.value if r.final_status else "Pending"
        }
        for r in records
    ]
