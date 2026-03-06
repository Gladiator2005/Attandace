from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.audit import log_action
from app.crud.subject_attendance import admin_resolve_attendance as resolve_subject_attendance
from app.models.audit_log import AuditAction
from app.models.subject_attendance import SubjectAttendance
from app.models.user import User, UserRole


async def resolve_disputed_record(
    db: AsyncSession,
    record_id: int,
    final_status: str,
    actor: User,
    notes: str | None = None,
) -> SubjectAttendance:
    """Resolve a disputed subject attendance record with role-aware checks."""
    if actor.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=403, detail="Admin or Mentor access required")

    if final_status not in ("Present", "Absent"):
        raise HTTPException(status_code=400, detail="final_status must be 'Present' or 'Absent'")

    result = await db.execute(
        select(SubjectAttendance)
        .options(selectinload(SubjectAttendance.student))
        .where(SubjectAttendance.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    if actor.role == UserRole.MENTOR:
        student = record.student
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        if (
            student.program != actor.program
            or student.major != actor.major
            or student.specialization != actor.specialization
            or student.section != actor.section
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only resolve disputes for students in your specific assigned cohort.",
            )

    old_status = record.final_status.value if record.final_status else "Unknown"
    resolved = await resolve_subject_attendance(db, record_id, final_status, actor.id)
    if not resolved:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    await log_action(
        db,
        AuditAction.RESOLVE_DISPUTE,
        actor=actor,
        target_type="SubjectAttendance",
        target_id=resolved.id,
        target_user_id=resolved.student_id,
        old_value={"final_status": old_status},
        new_value={"final_status": resolved.final_status.value, "notes": notes},
        description=(
            f"{actor.role.value} {actor.email} resolved dispute "
            f"for subject attendance #{resolved.id} to {resolved.final_status.value}"
        ),
    )
    await db.commit()
    return resolved
