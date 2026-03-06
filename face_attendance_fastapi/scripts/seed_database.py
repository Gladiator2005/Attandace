"""Database seeding utilities for development and testing."""
import asyncio
import logging
from datetime import date, timedelta
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.subject_enrollment import SubjectEnrollment
from app.models.subject_attendance import SubjectAttendance, FinalStatus, AttendanceStatus
from app.models.academic_session import AcademicSession
from app.utils.security import hash_password

logger = logging.getLogger(__name__)


async def seed_users():
    """Create sample users for testing."""
    async with AsyncSessionLocal() as db:
        # Check if users already exist
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            logger.info("Users already exist, skipping seed")
            return

        users = [
            # Admin
            User(
                employee_id="ADMIN001",
                first_name="Admin",
                last_name="User",
                email="admin@university.edu",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                department="Administration",
                is_active=True,
            ),
            # Faculty
            User(
                employee_id="FAC001",
                first_name="Dr. John",
                last_name="Smith",
                email="john.smith@university.edu",
                phone="+1234567890",
                department="Computer Science",
                hashed_password=hash_password("faculty123"),
                role=UserRole.FACULTY,
                is_active=True,
            ),
            User(
                employee_id="FAC002",
                first_name="Dr. Sarah",
                last_name="Johnson",
                email="sarah.johnson@university.edu",
                department="Computer Science",
                hashed_password=hash_password("faculty123"),
                role=UserRole.FACULTY,
                is_active=True,
            ),
            # Mentors
            User(
                employee_id="MENT001",
                first_name="Michael",
                last_name="Brown",
                email="michael.brown@university.edu",
                program="B.Tech",
                major="Computer Science",
                section="A",
                department="Computer Science",
                hashed_password=hash_password("mentor123"),
                role=UserRole.MENTOR,
                is_active=True,
            ),
            # Students
            User(
                employee_id="STU001",
                first_name="Alice",
                last_name="Williams",
                email="alice.williams@students.edu",
                program="B.Tech",
                major="Computer Science",
                section="A",
                semester=5,
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                is_active=True,
            ),
            User(
                employee_id="STU002",
                first_name="Bob",
                last_name="Davis",
                email="bob.davis@students.edu",
                program="B.Tech",
                major="Computer Science",
                section="A",
                semester=5,
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                is_active=True,
            ),
            User(
                employee_id="STU003",
                first_name="Carol",
                last_name="Miller",
                email="carol.miller@students.edu",
                program="B.Tech",
                major="Computer Science",
                section="B",
                semester=5,
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                is_active=True,
            ),
        ]

        db.add_all(users)
        await db.commit()
        logger.info(f"Created {len(users)} users")


async def seed_subjects():
    """Create sample subjects."""
    async with AsyncSessionLocal() as db:
        # Check if subjects already exist
        result = await db.execute(select(Subject).limit(1))
        if result.scalar_one_or_none():
            logger.info("Subjects already exist, skipping seed")
            return

        # Get faculty users
        faculty_result = await db.execute(
            select(User).where(User.role == UserRole.FACULTY)
        )
        faculty = faculty_result.scalars().all()

        if not faculty:
            logger.warning("No faculty found, cannot create subjects")
            return

        subjects = [
            Subject(
                code="CS101",
                name="Introduction to Programming",
                department="Computer Science",
                semester=1,
                total_classes=40,
                faculty_id=faculty[0].id,
                attendance_threshold=75.0,
            ),
            Subject(
                code="CS201",
                name="Data Structures and Algorithms",
                department="Computer Science",
                semester=3,
                total_classes=45,
                faculty_id=faculty[0].id if len(faculty) > 0 else None,
                attendance_threshold=80.0,
            ),
            Subject(
                code="CS301",
                name="Database Management Systems",
                department="Computer Science",
                semester=5,
                total_classes=42,
                faculty_id=faculty[1].id if len(faculty) > 1 else faculty[0].id,
                attendance_threshold=75.0,
            ),
        ]

        db.add_all(subjects)
        await db.commit()
        logger.info(f"Created {len(subjects)} subjects")


async def seed_enrollments():
    """Enroll students in subjects."""
    async with AsyncSessionLocal() as db:
        # Check if enrollments already exist
        result = await db.execute(select(SubjectEnrollment).limit(1))
        if result.scalar_one_or_none():
            logger.info("Enrollments already exist, skipping seed")
            return

        # Get students and subjects
        students_result = await db.execute(
            select(User).where(User.role == UserRole.STUDENT)
        )
        students = students_result.scalars().all()

        subjects_result = await db.execute(select(Subject))
        subjects = subjects_result.scalars().all()

        if not students or not subjects:
            logger.warning("No students or subjects found, cannot create enrollments")
            return

        enrollments = []
        for student in students:
            for subject in subjects:
                # Enroll students in subjects matching their semester
                if subject.semester == student.semester or subject.semester == 1:
                    enrollments.append(
                        SubjectEnrollment(
                            student_id=student.id,
                            subject_id=subject.id,
                        )
                    )

        db.add_all(enrollments)
        await db.commit()
        logger.info(f"Created {len(enrollments)} enrollments")


async def seed_attendance():
    """Create sample attendance records for the last 10 days."""
    async with AsyncSessionLocal() as db:
        # Check if attendance already exists
        result = await db.execute(select(SubjectAttendance).limit(1))
        if result.scalar_one_or_none():
            logger.info("Attendance already exists, skipping seed")
            return

        # Get enrollments
        enrollments_result = await db.execute(select(SubjectEnrollment))
        enrollments = enrollments_result.scalars().all()

        if not enrollments:
            logger.warning("No enrollments found, cannot create attendance")
            return

        import random

        attendance_records = []
        today = date.today()

        # Create attendance for last 10 days
        for day_offset in range(10):
            attendance_date = today - timedelta(days=day_offset)

            for enrollment in enrollments:
                # 80% chance of being present
                is_present = random.random() < 0.8

                # Simulate both verification methods with some discrepancies
                face_verified = is_present and random.random() < 0.9  # 90% face scan if present
                faculty_marked = is_present and random.random() < 0.95  # 95% marked if present

                # Determine final status
                if face_verified and faculty_marked:
                    final_status = FinalStatus.PRESENT
                elif not face_verified and not faculty_marked:
                    final_status = FinalStatus.ABSENT
                elif face_verified or faculty_marked:
                    # One verified but not both - disputed
                    final_status = FinalStatus.DISPUTED
                else:
                    final_status = FinalStatus.PENDING

                attendance_records.append(
                    SubjectAttendance(
                        student_id=enrollment.student_id,
                        subject_id=enrollment.subject_id,
                        date=attendance_date,
                        status=AttendanceStatus.PRESENT if is_present else AttendanceStatus.ABSENT,
                        face_verified=face_verified,
                        faculty_marked=faculty_marked,
                        final_status=final_status,
                    )
                )

        db.add_all(attendance_records)
        await db.commit()
        logger.info(f"Created {len(attendance_records)} attendance records")


async def seed_all():
    """Run all seed functions."""
    logger.info("Starting database seeding...")
    await seed_users()
    await seed_subjects()
    await seed_enrollments()
    await seed_attendance()
    logger.info("Database seeding complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_all())
