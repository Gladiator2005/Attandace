"""Shared test fixtures and configuration."""
import pytest
import asyncio
from datetime import date
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.subject_attendance import SubjectAttendance, FinalStatus
from app.utils.security import hash_password


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Clear rate limit cache before tests
    from app.middleware.rate_limit import _request_log
    _request_log.clear()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create test admin user."""
    user = User(
        employee_id="ADMIN001",
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def faculty_user(db_session: AsyncSession) -> User:
    """Create test faculty user."""
    user = User(
        employee_id="FAC001",
        first_name="Faculty",
        last_name="User",
        email="faculty@test.com",
        department="Computer Science",
        hashed_password=hash_password("faculty123"),
        role=UserRole.FACULTY,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def mentor_user(db_session: AsyncSession) -> User:
    """Create test mentor user."""
    user = User(
        employee_id="MENT001",
        first_name="Mentor",
        last_name="User",
        email="mentor@test.com",
        program="B.Tech",
        major="Computer Science",
        section="A",
        hashed_password=hash_password("mentor123"),
        role=UserRole.MENTOR,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def student_user(db_session: AsyncSession) -> User:
    """Create test student user."""
    user = User(
        employee_id="STU001",
        first_name="Student",
        last_name="User",
        email="student@test.com",
        program="B.Tech",
        major="Computer Science",
        section="A",
        semester=5,
        hashed_password=hash_password("student123"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_subject(db_session: AsyncSession, faculty_user: User) -> Subject:
    """Create test subject."""
    subject = Subject(
        code="CS101",
        name="Introduction to Programming",
        department="Computer Science",
        semester=1,
        faculty_id=faculty_user.id
    )
    db_session.add(subject)
    await db_session.commit()
    await db_session.refresh(subject)
    return subject


@pytest.fixture
async def disputed_attendance(
    db_session: AsyncSession, 
    student_user: User, 
    test_subject: Subject
) -> SubjectAttendance:
    """Create disputed attendance record for testing resolution."""
    attendance = SubjectAttendance(
        student_id=student_user.id,
        subject_id=test_subject.id,
        date=date.today(),
        face_verified=True,
        faculty_marked=False,
        final_status=FinalStatus.DISPUTED
    )
    db_session.add(attendance)
    await db_session.commit()
    await db_session.refresh(attendance)
    return attendance


@pytest.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Get JWT token for admin user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "admin123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def faculty_token(client: AsyncClient, faculty_user: User) -> str:
    """Get JWT token for faculty user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "faculty@test.com", "password": "faculty123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def mentor_token(client: AsyncClient, mentor_user: User) -> str:
    """Get JWT token for mentor user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "mentor@test.com", "password": "mentor123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def student_token(client: AsyncClient, student_user: User) -> str:
    """Get JWT token for student user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "student@test.com", "password": "student123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
