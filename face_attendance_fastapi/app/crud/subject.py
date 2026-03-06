from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional
from app.models.subject import Subject
from app.models.subject_enrollment import SubjectEnrollment
from app.models.user import User, UserRole


async def create_subject(db: AsyncSession, code: str, name: str, department: str = None,
                         semester: int = None, total_classes: int = 40, faculty_id: int = None,
                         session_id: int = None, attendance_threshold: float = 75.0) -> Subject:
    subject = Subject(code=code, name=name, department=department, semester=semester,
                      total_classes=total_classes, faculty_id=faculty_id,
                      session_id=session_id, attendance_threshold=attendance_threshold)
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


async def get_subject_by_id(db: AsyncSession, subject_id: int) -> Optional[Subject]:
    result = await db.execute(select(Subject).options(selectinload(Subject.faculty)).where(Subject.id == subject_id))
    return result.scalar_one_or_none()


async def get_subject_by_code(db: AsyncSession, code: str) -> Optional[Subject]:
    result = await db.execute(select(Subject).where(Subject.code == code))
    return result.scalar_one_or_none()


async def get_all_subjects(db: AsyncSession) -> List[Subject]:
    result = await db.execute(select(Subject).options(selectinload(Subject.faculty)).order_by(Subject.code))
    return result.scalars().all()


async def get_subjects_by_faculty(db: AsyncSession, faculty_id: int) -> List[Subject]:
    result = await db.execute(select(Subject).options(selectinload(Subject.faculty)).where(Subject.faculty_id == faculty_id).order_by(Subject.code))
    return result.scalars().all()


async def get_student_subjects(db: AsyncSession, student_id: int) -> List[Subject]:
    result = await db.execute(
        select(Subject).options(selectinload(Subject.faculty))
        .join(SubjectEnrollment, SubjectEnrollment.subject_id == Subject.id)
        .where(SubjectEnrollment.student_id == student_id)
        .order_by(Subject.code)
    )
    return result.scalars().all()


async def update_subject(db: AsyncSession, subject_id: int, **kwargs) -> Optional[Subject]:
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(subject, key, value)
    await db.commit()
    await db.refresh(subject)
    return subject


async def delete_subject(db: AsyncSession, subject_id: int) -> bool:
    subject = await get_subject_by_id(db, subject_id)
    if not subject:
        return False
    await db.delete(subject)
    await db.commit()
    return True


async def enroll_students(db: AsyncSession, subject_id: int, student_ids: List[int]):
    for sid in student_ids:
        existing = await db.execute(
            select(SubjectEnrollment).where(
                SubjectEnrollment.student_id == sid,
                SubjectEnrollment.subject_id == subject_id
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(SubjectEnrollment(student_id=sid, subject_id=subject_id))
    await db.commit()


async def unenroll_student(db: AsyncSession, subject_id: int, student_id: int):
    await db.execute(
        delete(SubjectEnrollment).where(
            SubjectEnrollment.student_id == student_id,
            SubjectEnrollment.subject_id == subject_id
        )
    )
    await db.commit()


async def get_enrolled_students(db: AsyncSession, subject_id: int) -> List[User]:
    result = await db.execute(
        select(User).join(SubjectEnrollment, SubjectEnrollment.student_id == User.id)
        .where(SubjectEnrollment.subject_id == subject_id)
        .order_by(User.employee_id)
    )
    return result.scalars().all()


async def get_enrollment_count(db: AsyncSession, subject_id: int) -> int:
    result = await db.execute(
        select(func.count(SubjectEnrollment.id)).where(SubjectEnrollment.subject_id == subject_id)
    )
    return result.scalar() or 0
