import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.utils.security import get_current_user, hash_password
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.subject_enrollment import SubjectEnrollment

router = APIRouter()


@router.post("/students")
async def bulk_import_students(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload CSV to create students in bulk.
    CSV columns: enrollment_no, first_name, last_name, email, department, program, major, specialization, section, semester, password
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):  # start=2 because header is row 1
        try:
            enrollment_no = row.get("enrollment_no", "").strip()
            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            email = row.get("email", "").strip()
            department = row.get("department", "").strip()
            program = row.get("program", "").strip()
            major = row.get("major", "").strip()
            specialization = row.get("specialization", "").strip()
            section = row.get("section", "").strip()
            semester = row.get("semester", "").strip()
            password = row.get("password", "").strip() or "changeme123"

            if not all([enrollment_no, first_name, last_name, email]):
                errors.append(f"Row {i}: missing required fields")
                skipped += 1
                continue

            # Check duplicates
            existing = await db.execute(
                select(User).where((User.email == email) | (User.employee_id == enrollment_no))
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            user = User(
                employee_id=enrollment_no,
                first_name=first_name,
                last_name=last_name,
                email=email,
                department=department or None,
                program=program or None,
                major=major or None,
                specialization=specialization or None,
                section=section or None,
                semester=int(semester) if semester else None,
                hashed_password=hash_password(password),
                role=UserRole.STUDENT,
            )
            db.add(user)
            created += 1

        except Exception as ex:
            errors.append(f"Row {i}: {str(ex)}")
            skipped += 1

    await db.commit()
    return {
        "message": f"Import complete: {created} created, {skipped} skipped",
        "created": created,
        "skipped": skipped,
        "errors": errors[:20],  # limit error list
    }


@router.post("/enroll")
async def bulk_enroll_students(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload CSV to enroll students into subjects.
    CSV columns: enrollment_no, subject_code
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    enrolled = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            enrollment_no = row.get("enrollment_no", "").strip()
            subject_code = row.get("subject_code", "").strip()

            if not enrollment_no or not subject_code:
                errors.append(f"Row {i}: missing enrollment_no or subject_code")
                skipped += 1
                continue

            # Find user
            user_result = await db.execute(
                select(User).where(User.employee_id == enrollment_no)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                errors.append(f"Row {i}: student '{enrollment_no}' not found")
                skipped += 1
                continue

            # Find subject
            sub_result = await db.execute(
                select(Subject).where(Subject.code == subject_code)
            )
            subject = sub_result.scalar_one_or_none()
            if not subject:
                errors.append(f"Row {i}: subject '{subject_code}' not found")
                skipped += 1
                continue

            # Check already enrolled
            existing = await db.execute(
                select(SubjectEnrollment).where(
                    SubjectEnrollment.student_id == user.id,
                    SubjectEnrollment.subject_id == subject.id,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            db.add(SubjectEnrollment(student_id=user.id, subject_id=subject.id))
            enrolled += 1

        except Exception as ex:
            errors.append(f"Row {i}: {str(ex)}")
            skipped += 1

    await db.commit()
    return {
        "message": f"Enrollment complete: {enrolled} enrolled, {skipped} skipped",
        "enrolled": enrolled,
        "skipped": skipped,
        "errors": errors[:20],
    }
