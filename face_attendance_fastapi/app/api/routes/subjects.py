from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.subject import (
    create_subject, get_all_subjects, get_subject_by_id, get_subject_by_code,
    get_subjects_by_faculty, get_student_subjects, update_subject, delete_subject,
    enroll_students, get_enrolled_students, get_enrollment_count, unenroll_student,
)
from app.crud.subject_attendance import (
    mark_faculty_attendance, mark_face_attendance, reconcile_attendance,
    get_disputed_records, get_subject_attendance_records, get_classes_conducted,
    get_student_attendance_count, calculate_threshold,
)
from app.services.dispute_resolution_service import resolve_disputed_record
from app.schemas.subject import (
    SubjectCreate, SubjectUpdate, SubjectResponse, EnrollStudentsRequest,
    MarkAttendanceRequest,
)

router = APIRouter()


# ── Subject CRUD ──

@router.post("/")
async def create_new_subject(
    data: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    existing = await get_subject_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Subject code '{data.code}' already exists")
    subject = await create_subject(
        db, code=data.code, name=data.name, department=data.department,
        semester=data.semester, total_classes=data.total_classes, faculty_id=data.faculty_id,
    )
    return {"id": subject.id, "code": subject.code, "name": subject.name, "message": "Subject created"}


@router.get("/")
async def list_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.ADMIN:
        subjects = await get_all_subjects(db)
    elif current_user.role == UserRole.FACULTY:
        subjects = await get_subjects_by_faculty(db, current_user.id)
    else:
        subjects = await get_student_subjects(db, current_user.id)

    result = []
    for s in subjects:
        count = await get_enrollment_count(db, s.id)
        faculty_name = None
        if s.faculty:
            faculty_name = s.faculty.full_name
        result.append({
            "id": s.id, "code": s.code, "name": s.name,
            "department": s.department, "semester": s.semester,
            "total_classes": s.total_classes, "faculty_id": s.faculty_id,
            "faculty_name": faculty_name, "enrolled_count": count,
        })
    return result


@router.get("/{subject_id}")
async def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    count = await get_enrollment_count(db, subject_id)
    conducted = await get_classes_conducted(db, subject_id)
    faculty_name = subject.faculty.full_name if subject.faculty else None
    return {
        "id": subject.id, "code": subject.code, "name": subject.name,
        "department": subject.department, "semester": subject.semester,
        "total_classes": subject.total_classes, "faculty_id": subject.faculty_id,
        "faculty_name": faculty_name, "enrolled_count": count,
        "classes_conducted": conducted,
    }


@router.put("/{subject_id}")
async def update_existing_subject(
    subject_id: int, data: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    updated = await update_subject(db, subject_id, **data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Subject not found")
    return {"message": "Subject updated"}


@router.delete("/{subject_id}")
async def delete_existing_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    deleted = await delete_subject(db, subject_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subject not found")
    return {"message": "Subject deleted"}


# ── Enrollment ──

@router.post("/{subject_id}/enroll")
async def enroll_students_in_subject(
    subject_id: int,
    data: EnrollStudentsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await enroll_students(db, subject_id, data.student_ids)
    return {"message": f"Enrolled {len(data.student_ids)} students"}


@router.get("/{subject_id}/students")
async def get_subject_students(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    students = await get_enrolled_students(db, subject_id)
    return [
        {"id": s.id, "enrollment_no": s.employee_id, "name": s.full_name,
         "department": s.department, "semester": s.semester}
        for s in students
    ]


# ── Faculty marks roll call ──

@router.post("/{subject_id}/attendance")
async def mark_subject_attendance(
    subject_id: int,
    data: MarkAttendanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students use face scan, not manual marking")
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    att_date = date.fromisoformat(data.date)
    entries = [{"student_id": e.student_id, "status": e.status} for e in data.entries]
    try:
        await mark_faculty_attendance(db, subject_id, entries, current_user.id, att_date,
                                      is_admin=(current_user.role == UserRole.ADMIN))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Faculty attendance marked for {len(entries)} students on {data.date}"}


# ── Student face scan ──

class FaceScanRequest(BaseModel):
    subject_id: Optional[int] = None  # if None, auto-detect from schedule


@router.post("/face-scan")
async def face_scan_attendance(
    data: FaceScanRequest = FaceScanRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student scans face — auto-detects subject from schedule or uses provided subject_id."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Face scan is for students only")

    subject_id = data.subject_id
    if not subject_id:
        # Auto-detect from schedule
        from datetime import datetime
        from app.crud.schedule import get_current_subject_for_student
        now = datetime.now()
        subject = await get_current_subject_for_student(
            db, current_user.id, now.weekday(), now.time()
        )
        if not subject:
            raise HTTPException(status_code=400, detail="No class scheduled right now. Please select a subject manually.")
        subject_id = subject.id

    today = date.today()
    try:
        record = await mark_face_attendance(db, current_user.id, subject_id, today)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    sub = await get_subject_by_id(db, subject_id)
    return {
        "message": f"Face verified for {sub.code} – {sub.name}",
        "subject_code": sub.code,
        "subject_name": sub.name,
        "date": today.isoformat(),
        "face_verified": True,
    }


# ── Reconciliation ──

@router.post("/{subject_id}/reconcile")
async def reconcile_subject_attendance(
    subject_id: int,
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Faculty/Admin triggers reconciliation for a subject on a date."""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    att_date = date.fromisoformat(date_str)
    summary = await reconcile_attendance(db, subject_id, att_date)
    return {"message": "Reconciliation complete", "summary": summary}


# ── Admin resolve disputed record ──

class ResolveRequest(BaseModel):
    final_status: str  # "Present" or "Absent"


@router.post("/attendance/{record_id}/resolve")
async def resolve_disputed_attendance(
    record_id: int,
    data: ResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_disputed_record(
        db=db,
        record_id=record_id,
        final_status=data.final_status,
        actor=current_user,
    )
    return {"message": f"Record resolved as {resolved.final_status.value}"}


# ── Get disputed records ──

@router.get("/disputed/all")
async def list_disputed_records(
    subject_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    records = await get_disputed_records(db, subject_id)
    return [
        {
            "id": r.id, "student_id": r.student_id,
            "student_name": r.student.full_name if r.student else "",
            "enrollment_no": r.student.employee_id if r.student else "",
            "subject_id": r.subject_id,
            "subject_code": r.subject.code if r.subject else "",
            "subject_name": r.subject.name if r.subject else "",
            "date": r.date.isoformat(),
            "face_verified": r.face_verified,
            "faculty_marked": r.faculty_marked,
            "final_status": r.final_status.value if r.final_status else "Pending",
        }
        for r in records
    ]


@router.get("/{subject_id}/attendance")
async def get_attendance(
    subject_id: int,
    date_str: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    att_date = date.fromisoformat(date_str) if date_str else None
    records = await get_subject_attendance_records(db, subject_id, att_date)
    return [
        {
            "id": r.id, "student_id": r.student_id,
            "student_name": r.student.full_name if r.student else "",
            "enrollment_no": r.student.employee_id if r.student else "",
            "date": r.date.isoformat(), "status": r.status.value,
            "face_verified": r.face_verified, "faculty_marked": r.faculty_marked,
            "final_status": r.final_status.value if r.final_status else "Pending",
        }
        for r in records
    ]


@router.get("/{subject_id}/stats")
async def subject_stats(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    conducted = await get_classes_conducted(db, subject_id)
    students = await get_enrolled_students(db, subject_id)
    stats = []
    for s in students:
        attended = await get_student_attendance_count(db, s.id, subject_id)
        calc = calculate_threshold(attended, conducted, subject.total_classes)
        stats.append({
            "student_id": s.id, "enrollment_no": s.employee_id,
            "student_name": s.full_name, "department": s.department,
            "classes_attended": attended, "classes_conducted": conducted,
            **calc,
        })
    return {
        "subject": {"id": subject.id, "code": subject.code, "name": subject.name,
                     "total_classes": subject.total_classes, "classes_conducted": conducted},
        "students": stats,
    }
