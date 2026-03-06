"""Test attendance marking and retrieval."""
import pytest
from datetime import date
from httpx import AsyncClient
from app.models.user import User
from app.models.subject import Subject


@pytest.mark.asyncio
class TestAttendanceMarking:
    """Test attendance marking operations."""

    async def test_mark_subject_attendance_as_faculty(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject,
        student_user: User
    ):
        """Test faculty can mark attendance for their subject."""
        response = await client.post(
            f"/api/subjects/{test_subject.id}/attendance",
            headers={"Authorization": f"Bearer {faculty_token}"},
            json={
                "date": str(date.today()),
                "entries": [
                    {
                        "student_id": student_user.id,
                        "status": "Present"
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "marked" in data.get("message", "").lower() or "success" in data.get("message", "").lower()

    async def test_get_subject_attendance(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject
    ):
        """Test retrieving attendance records for a subject."""
        response = await client.get(
            f"/api/subjects/{test_subject.id}/attendance",
            headers={"Authorization": f"Bearer {faculty_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)

    async def test_student_cannot_mark_attendance(
        self,
        client: AsyncClient,
        student_token: str,
        test_subject: Subject,
        student_user: User
    ):
        """Test students cannot manually mark attendance."""
        response = await client.post(
            f"/api/subjects/{test_subject.id}/attendance",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "date": str(date.today()),
                "entries": [
                    {
                        "student_id": student_user.id,
                        "status": "Present"
                    }
                ]
            }
        )
        # Should be 403 Forbidden
        assert response.status_code == 403

    async def test_get_student_own_attendance(
        self,
        client: AsyncClient,
        student_token: str,
        student_user: User
    ):
        """Test student can view their own attendance."""
        response = await client.get(
            f"/api/attendance/student/{student_user.id}",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        # Should succeed or return empty list
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestAttendanceRecords:
    """Test attendance record retrieval."""

    async def test_list_subjects_as_faculty(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject
    ):
        """Test faculty can list subjects."""
        response = await client.get(
            "/api/subjects/",
            headers={"Authorization": f"Bearer {faculty_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_subject_details(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject
    ):
        """Test retrieving subject details."""
        response = await client.get(
            f"/api/subjects/{test_subject.id}",
            headers={"Authorization": f"Bearer {faculty_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == test_subject.code
        assert data["name"] == test_subject.name
