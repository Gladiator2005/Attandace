from datetime import date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.leave_request import LeaveRequest, LeaveStatus, LeaveType
from app.models.subject_attendance import SubjectAttendance, AttendanceStatus, FinalStatus
from app.models.subject import Subject
from app.models.user import User
from app.crud.notifications import create_notification
from app.models.attendance_notification import NotificationType


async def create_leave_request(db: AsyncSession, student_id: int, subject_id: int,
                                leave_date: date, leave_type: str, reason: str) -> LeaveRequest:
    """Student submits a leave request."""
    # Check for duplicate
    existing = await db.execute(
        select(LeaveRequest).where(
            LeaveRequest.student_id == student_id,
            LeaveRequest.subject_id == subject_id,
            LeaveRequest.leave_date == leave_date,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Leave request already exists for this date and subject.")

    leave = LeaveRequest(
        student_id=student_id,
        subject_id=subject_id,
        leave_date=leave_date,
        leave_type=LeaveType(leave_type),
        reason=reason,
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)

    # Notify faculty
    sub_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = sub_result.scalar_one_or_none()
    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()
    if subject and subject.faculty_id and student:
        await create_notification(
            db, subject.faculty_id, subject_id, NotificationType.FACE_ONLY,
            f"{student.full_name} requested {leave_type} leave for {subject.code} on {leave_date}. Reason: {reason}",
            None
        )
        await db.commit()

    return leave


async def get_pending_leaves(db: AsyncSession, faculty_id: int = None) -> List[LeaveRequest]:
    """Get pending leave requests. If faculty_id, only for their subjects."""
    query = select(LeaveRequest).options(
        selectinload(LeaveRequest.student),
        selectinload(LeaveRequest.subject),
    ).where(LeaveRequest.status == LeaveStatus.PENDING)

    if faculty_id:
        # Only subjects this faculty teaches
        query = query.join(Subject, LeaveRequest.subject_id == Subject.id).where(
            Subject.faculty_id == faculty_id
        )

    query = query.order_by(LeaveRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_student_leaves(db: AsyncSession, student_id: int) -> List[LeaveRequest]:
    """Get all leave requests for a student."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.subject),
        ).where(LeaveRequest.student_id == student_id)
        .order_by(LeaveRequest.created_at.desc())
    )
    return result.scalars().all()


async def approve_leave(db: AsyncSession, leave_id: int, approved_by: int) -> Optional[LeaveRequest]:
    """Faculty/admin approves a leave request. Auto-adjusts attendance."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.student),
            selectinload(LeaveRequest.subject),
        ).where(LeaveRequest.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    if not leave:
        return None
    if leave.status != LeaveStatus.PENDING:
        raise ValueError("Leave request is not pending.")

    leave.status = LeaveStatus.APPROVED
    leave.approved_by = approved_by

    # Auto-create/update attendance record as Present
    existing = await db.execute(
        select(SubjectAttendance).where(
            SubjectAttendance.student_id == leave.student_id,
            SubjectAttendance.subject_id == leave.subject_id,
            SubjectAttendance.date == leave.leave_date,
        )
    )
    att_record = existing.scalar_one_or_none()
    if att_record:
        att_record.status = AttendanceStatus.PRESENT
        att_record.final_status = FinalStatus.PRESENT
        att_record.faculty_marked = True
    else:
        db.add(SubjectAttendance(
            student_id=leave.student_id,
            subject_id=leave.subject_id,
            date=leave.leave_date,
            status=AttendanceStatus.PRESENT,
            faculty_marked=True,
            face_verified=False,
            final_status=FinalStatus.PRESENT,
            marked_by=approved_by,
        ))

    # Notify student
    subject = leave.subject
    await create_notification(
        db, leave.student_id, leave.subject_id, NotificationType.RESOLVED,
        f"Your {leave.leave_type.value} leave for {subject.code} on {leave.leave_date} was APPROVED. Attendance adjusted.",
        None
    )

    await db.commit()
    await db.refresh(leave)
    return leave


async def reject_leave(db: AsyncSession, leave_id: int, approved_by: int) -> Optional[LeaveRequest]:
    """Faculty/admin rejects a leave request."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.subject),
        ).where(LeaveRequest.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    if not leave:
        return None
    if leave.status != LeaveStatus.PENDING:
        raise ValueError("Leave request is not pending.")

    leave.status = LeaveStatus.REJECTED
    leave.approved_by = approved_by

    subject = leave.subject
    await create_notification(
        db, leave.student_id, leave.subject_id, NotificationType.ABSENT,
        f"Your {leave.leave_type.value} leave for {subject.code} on {leave.leave_date} was REJECTED.",
        None
    )

    await db.commit()
    await db.refresh(leave)
    return leave
