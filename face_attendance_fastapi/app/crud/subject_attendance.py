import math
from datetime import date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.models.subject_attendance import SubjectAttendance, AttendanceStatus, FinalStatus
from app.models.subject import Subject
from app.models.subject_enrollment import SubjectEnrollment
from app.models.user import User, UserRole
from app.models.attendance_notification import NotificationType
from app.crud.notifications import create_notification
from app.services.email_service import send_absent_email
from app.config import settings

DEFAULT_THRESHOLD = 75.0
LOCK_DAYS = getattr(settings, 'attendance_lock_days', 3)


def _is_locked(att_date: date) -> bool:
    """Check if a date is outside the editable window."""
    if LOCK_DAYS <= 0:
        return False
    return (date.today() - att_date).days > LOCK_DAYS


# ── Faculty marks roll call ──
async def mark_faculty_attendance(db: AsyncSession, subject_id: int, entries: list,
                                   marked_by: int, att_date: date, is_admin: bool = False):
    """Faculty marks attendance. Sets faculty_marked=True for present students."""
    # Date validation
    if att_date > date.today():
        raise ValueError("Cannot mark attendance for a future date.")
    if _is_locked(att_date) and not is_admin:
        raise ValueError(f"Attendance for {att_date} is locked (older than {LOCK_DAYS} days). Only admin can edit.")

    for entry in entries:
        existing = await db.execute(
            select(SubjectAttendance).where(
                SubjectAttendance.student_id == entry["student_id"],
                SubjectAttendance.subject_id == subject_id,
                SubjectAttendance.date == att_date,
            )
        )
        record = existing.scalar_one_or_none()
        status = AttendanceStatus(entry.get("status", "Present"))
        is_present = status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)

        if record:
            if record.is_locked and not is_admin:
                continue  # Skip locked records for non-admin
            record.status = status
            record.faculty_marked = is_present
            record.marked_by = marked_by
        else:
            db.add(SubjectAttendance(
                student_id=entry["student_id"],
                subject_id=subject_id,
                date=att_date,
                status=status,
                faculty_marked=is_present,
                face_verified=False,
                final_status=FinalStatus.PENDING,
                marked_by=marked_by,
            ))
    await db.commit()


# ── Student face scan ──
async def mark_face_attendance(db: AsyncSession, student_id: int, subject_id: int,
                                att_date: date) -> SubjectAttendance:
    """Student scans face. Sets face_verified=True."""
    # Date validation — students can only scan for today
    if att_date != date.today():
        raise ValueError("Face scan is only allowed for today's date.")

    existing = await db.execute(
        select(SubjectAttendance).where(
            SubjectAttendance.student_id == student_id,
            SubjectAttendance.subject_id == subject_id,
            SubjectAttendance.date == att_date,
        )
    )
    record = existing.scalar_one_or_none()

    if record:
        if record.is_locked:
            raise ValueError("This attendance record is locked.")
        record.face_verified = True
        # Race condition fix: if already reconciled, set back to DISPUTED
        if record.final_status in (FinalStatus.ABSENT, FinalStatus.PRESENT):
            if not record.faculty_marked:
                record.final_status = FinalStatus.DISPUTED  # needs re-reconciliation
    else:
        record = SubjectAttendance(
            student_id=student_id,
            subject_id=subject_id,
            date=att_date,
            status=AttendanceStatus.PRESENT,
            face_verified=True,
            faculty_marked=False,
            final_status=FinalStatus.PENDING,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return record


# ── Reconciliation ──
async def reconcile_attendance(db: AsyncSession, subject_id: int, att_date: date):
    """Compare face_verified vs faculty_marked for all enrolled students.
    Returns summary of actions taken."""
    enrolled = await db.execute(
        select(SubjectEnrollment.student_id).where(SubjectEnrollment.subject_id == subject_id)
    )
    student_ids = [row[0] for row in enrolled.all()]
    if not student_ids:
        return {"reconciled": 0}

    sub_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = sub_result.scalar_one_or_none()
    if not subject:
        return {"reconciled": 0}

    admin_result = await db.execute(
        select(User.id).where(User.role == UserRole.ADMIN, User.is_active == True)
    )
    admin_ids = [row[0] for row in admin_result.all()]

    summary = {"present": 0, "absent": 0, "face_only": 0, "faculty_only": 0}

    for sid in student_ids:
        result = await db.execute(
            select(SubjectAttendance).options(selectinload(SubjectAttendance.student))
            .where(
                SubjectAttendance.student_id == sid,
                SubjectAttendance.subject_id == subject_id,
                SubjectAttendance.date == att_date,
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            record = SubjectAttendance(
                student_id=sid, subject_id=subject_id, date=att_date,
                status=AttendanceStatus.ABSENT, face_verified=False,
                faculty_marked=False, final_status=FinalStatus.ABSENT,
            )
            db.add(record)
            await db.flush()

        student_result = await db.execute(select(User).where(User.id == sid))
        student = student_result.scalar_one_or_none()
        student_name = student.full_name if student else "Unknown"
        student_email = student.email if student else None

        if record.face_verified and record.faculty_marked:
            record.final_status = FinalStatus.PRESENT
            record.status = AttendanceStatus.PRESENT
            summary["present"] += 1

        elif record.face_verified and not record.faculty_marked:
            record.final_status = FinalStatus.DISPUTED
            summary["face_only"] += 1
            await create_notification(db, sid, subject_id, NotificationType.FACE_ONLY,
                                      f"You scanned your face for {subject.code} but were not marked present by faculty. Please contact your faculty.", record.id)
            if subject.faculty_id:
                await create_notification(db, subject.faculty_id, subject_id, NotificationType.FACE_ONLY,
                                          f"{student_name} scanned face for {subject.code} on {att_date} but was not in your roll call.", record.id)
            
            # Find specific Mentor for this student's cohort
            mentor_result = await db.execute(
                select(User.id).where(
                    User.role == UserRole.MENTOR,
                    User.is_active == True,
                    User.program == student.program,
                    User.major == student.major,
                    User.specialization == student.specialization,
                    User.section == student.section
                )
            )
            mentor_ids = [row[0] for row in mentor_result.all()]
            notify_ids = mentor_ids if mentor_ids else admin_ids  # Fallback to Admin if no exact Mentor
            
            for nid in notify_ids:
                await create_notification(db, nid, subject_id, NotificationType.FACE_ONLY,
                                          f"{student_name} scanned face for {subject.code} on {att_date} but was NOT marked by faculty.", record.id)

        elif not record.face_verified and record.faculty_marked:
            record.final_status = FinalStatus.DISPUTED
            summary["faculty_only"] += 1
            await create_notification(db, sid, subject_id, NotificationType.FACULTY_ONLY,
                                      f"You were marked present by faculty in {subject.code} but did not scan your face. Only your mentor can verify.", record.id)
            if subject.faculty_id:
                await create_notification(db, subject.faculty_id, subject_id, NotificationType.FACULTY_ONLY,
                                          f"{student_name} is in your roll call for {subject.code} on {att_date} but did not scan face.", record.id)
            
            # Find specific Mentor for this student's cohort
            mentor_result = await db.execute(
                select(User.id).where(
                    User.role == UserRole.MENTOR,
                    User.is_active == True,
                    User.program == student.program,
                    User.major == student.major,
                    User.specialization == student.specialization,
                    User.section == student.section
                )
            )
            mentor_ids = [row[0] for row in mentor_result.all()]
            notify_ids = mentor_ids if mentor_ids else admin_ids  # Fallback to Admin if no exact Mentor
            
            for nid in notify_ids:
                await create_notification(db, nid, subject_id, NotificationType.FACULTY_ONLY,
                                          f"{student_name} was marked by faculty in {subject.code} on {att_date} but did NOT scan face.", record.id)

        else:
            record.final_status = FinalStatus.ABSENT
            record.status = AttendanceStatus.ABSENT
            summary["absent"] += 1
            await create_notification(db, sid, subject_id, NotificationType.ABSENT,
                                      f"You were marked absent in {subject.code} on {att_date}.", record.id)
            if student_email:
                await send_absent_email(student_email, student_name, subject.name, subject.code, str(att_date))

    await db.commit()
    return summary


# ── Admin resolve ──
async def admin_resolve_attendance(db: AsyncSession, record_id: int, final_status: str,
                                    admin_id: int) -> Optional[SubjectAttendance]:
    """Admin resolves a disputed attendance record. Admin bypasses locking."""
    result = await db.execute(
        select(SubjectAttendance).options(selectinload(SubjectAttendance.student))
        .where(SubjectAttendance.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None

    record.final_status = FinalStatus(final_status)
    record.resolved_by = admin_id
    if final_status == "Present":
        record.status = AttendanceStatus.PRESENT
    elif final_status == "Absent":
        record.status = AttendanceStatus.ABSENT
    await db.commit()
    await db.refresh(record)

    student = record.student
    sub_result = await db.execute(select(Subject).where(Subject.id == record.subject_id))
    subject = sub_result.scalar_one_or_none()
    if student and subject:
        status_text = "PRESENT" if final_status == "Present" else "ABSENT"
        await create_notification(db, record.student_id, record.subject_id, NotificationType.RESOLVED,
                                  f"Admin resolved your {subject.code} attendance for {record.date}: {status_text}.", record.id)
        if final_status == "Absent" and student.email:
            await send_absent_email(student.email, student.full_name, subject.name, subject.code, str(record.date))
    await db.commit()
    return record


# ── Lock old records ──
async def lock_old_attendance(db: AsyncSession):
    """Lock attendance records older than LOCK_DAYS. Called periodically or on demand."""
    cutoff = date.today() - timedelta(days=LOCK_DAYS)
    result = await db.execute(
        select(SubjectAttendance).where(
            SubjectAttendance.date <= cutoff,
            SubjectAttendance.is_locked == False,
        )
    )
    records = result.scalars().all()
    for r in records:
        r.is_locked = True
    await db.commit()
    return len(records)


# ── Get disputed records ──
async def get_disputed_records(db: AsyncSession, subject_id: int = None) -> list:
    query = select(SubjectAttendance).options(
        selectinload(SubjectAttendance.student),
        selectinload(SubjectAttendance.subject),
    ).where(SubjectAttendance.final_status == FinalStatus.DISPUTED)
    if subject_id:
        query = query.where(SubjectAttendance.subject_id == subject_id)
    query = query.order_by(SubjectAttendance.date.desc())
    result = await db.execute(query)
    return result.scalars().all()


# ── Existing helpers ──
async def get_classes_conducted(db: AsyncSession, subject_id: int) -> int:
    result = await db.execute(
        select(func.count(func.distinct(SubjectAttendance.date)))
        .where(SubjectAttendance.subject_id == subject_id)
    )
    return result.scalar() or 0


async def get_student_attendance_count(db: AsyncSession, student_id: int, subject_id: int) -> int:
    """Count classes where student is present (final_status preferred)."""
    result = await db.execute(
        select(func.count(SubjectAttendance.id)).where(
            SubjectAttendance.student_id == student_id,
            SubjectAttendance.subject_id == subject_id,
            SubjectAttendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]),
        )
    )
    return result.scalar() or 0


async def get_subject_attendance_records(db: AsyncSession, subject_id: int, att_date: date = None):
    query = select(SubjectAttendance).options(
        selectinload(SubjectAttendance.student)
    ).where(SubjectAttendance.subject_id == subject_id)
    if att_date:
        query = query.where(SubjectAttendance.date == att_date)
    query = query.order_by(SubjectAttendance.date.desc())
    result = await db.execute(query)
    return result.scalars().all()


def calculate_threshold(attended: int, conducted: int, total_scheduled: int,
                        threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Calculate attendance threshold status. threshold is configurable per-subject."""
    percentage = (attended / conducted * 100) if conducted > 0 else 100.0
    above_threshold = percentage >= threshold
    remaining = max(0, total_scheduled - conducted)
    target = math.ceil(threshold / 100 * total_scheduled)
    days_needed = max(0, target - attended)
    if days_needed > remaining:
        days_needed = remaining
    if attended >= target:
        days_off = attended + remaining - target
    else:
        days_off = 0
    return {
        "percentage": round(percentage, 1),
        "above_threshold": above_threshold,
        "days_needed": days_needed,
        "days_off": days_off,
        "threshold": threshold,
    }


async def get_student_threshold_status(db: AsyncSession, student_id: int) -> list:
    subjects = await db.execute(
        select(Subject).join(SubjectEnrollment, SubjectEnrollment.subject_id == Subject.id)
        .where(SubjectEnrollment.student_id == student_id)
        .order_by(Subject.code)
    )
    results = []
    for subject in subjects.scalars().all():
        conducted = await get_classes_conducted(db, subject.id)
        attended = await get_student_attendance_count(db, student_id, subject.id)
        sub_threshold = getattr(subject, 'attendance_threshold', None) or DEFAULT_THRESHOLD
        calc = calculate_threshold(attended, conducted, subject.total_classes, sub_threshold)
        results.append({
            "subject_id": subject.id, "subject_code": subject.code,
            "subject_name": subject.name, "total_scheduled": subject.total_classes,
            "classes_conducted": conducted, "classes_attended": attended, **calc,
        })
    return results


async def get_all_students_threshold(db: AsyncSession, subject_id: int = None) -> list:
    if subject_id:
        result = await db.execute(select(Subject).where(Subject.id == subject_id))
        subjects = [s for s in [result.scalar_one_or_none()] if s]
    else:
        result = await db.execute(select(Subject).order_by(Subject.code))
        subjects = result.scalars().all()

    rows = []
    for subject in subjects:
        conducted = await get_classes_conducted(db, subject.id)
        sub_threshold = getattr(subject, 'attendance_threshold', None) or DEFAULT_THRESHOLD
        students = await db.execute(
            select(User).join(SubjectEnrollment, SubjectEnrollment.student_id == User.id)
            .where(SubjectEnrollment.subject_id == subject.id)
            .order_by(User.employee_id)
        )
        for student in students.scalars().all():
            attended = await get_student_attendance_count(db, student.id, subject.id)
            calc = calculate_threshold(attended, conducted, subject.total_classes, sub_threshold)
            rows.append({
                "student_id": student.id, "student_name": student.full_name,
                "enrollment_no": student.employee_id, "department": student.department,
                "subject_code": subject.code, "subject_name": subject.name,
                "classes_attended": attended, "classes_conducted": conducted, **calc,
            })
    return rows
