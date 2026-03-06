from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.models.subject_attendance import SubjectAttendance, FinalStatus, AttendanceStatus
from datetime import date as date_type

router = APIRouter()


@router.get("/{subject_id}")
async def get_calendar_data(
    subject_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return day-by-day attendance status for the calendar view."""
    from app.models.leave_request import LeaveRequest, LeaveStatus

    student_id = current_user.id if current_user.role == UserRole.STUDENT else None

    # For admin/faculty: show aggregate (% present that day across all students)
    if student_id:
        att_q = select(SubjectAttendance).where(
            SubjectAttendance.student_id == student_id,
            SubjectAttendance.subject_id == subject_id,
        )
        leave_q = select(LeaveRequest).where(
            LeaveRequest.student_id == student_id,
            LeaveRequest.subject_id == subject_id,
            LeaveRequest.status == LeaveStatus.APPROVED,
        )
    else:
        att_q = select(SubjectAttendance).where(SubjectAttendance.subject_id == subject_id)
        leave_q = None

    # Filter by month/year
    import calendar as cal_mod
    first_day = date_type(year, month, 1)
    last_day = date_type(year, month, cal_mod.monthrange(year, month)[1])

    att_result = await db.execute(
        att_q.where(
            SubjectAttendance.date >= first_day,
            SubjectAttendance.date <= last_day,
        )
    )
    records = att_result.scalars().all()

    leave_records = []
    if leave_q is not None:
        lr = await db.execute(
            leave_q.where(
                LeaveRequest.leave_date >= first_day,
                LeaveRequest.leave_date <= last_day,
            )
        )
        leave_records = lr.scalars().all()

    leave_dates = {str(l.leave_date) for l in leave_records}

    # Build calendar data
    day_map = {}
    for r in records:
        d = str(r.date)
        if d in leave_dates:
            day_map[d] = "leave"
        elif r.final_status == FinalStatus.PRESENT or r.status == AttendanceStatus.PRESENT:
            day_map[d] = "present"
        elif r.final_status == FinalStatus.ABSENT or r.status == AttendanceStatus.ABSENT:
            day_map[d] = "absent"
        elif r.final_status == FinalStatus.DISPUTED:
            day_map[d] = "disputed"
        else:
            day_map[d] = "pending"

    # Add leave days not yet in records
    for d in leave_dates:
        if d not in day_map:
            day_map[d] = "leave"

    return {
        "subject_id": subject_id,
        "year": year,
        "month": month,
        "days": [{"date": k, "status": v} for k, v in sorted(day_map.items())],
    }
