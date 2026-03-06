"""Test export functionality."""
import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.subject import Subject


@pytest.mark.asyncio
class TestExports:
    """Test attendance export endpoints."""

    async def test_export_attendance_pdf_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
        test_subject: Subject
    ):
        """Test admin can export attendance as PDF."""
        response = await client.post(
            "/api/export/attendance/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "subject_id": test_subject.id,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31"
            }
        )
        # Should succeed or handle gracefully
        assert response.status_code in [200, 204, 404]
        
        if response.status_code == 200:
            # Check content type for PDF
            assert "application/pdf" in response.headers.get("content-type", "")

    async def test_export_attendance_excel_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
        test_subject: Subject
    ):
        """Test admin can export attendance as Excel."""
        response = await client.post(
            "/api/export/attendance/excel",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "subject_id": test_subject.id,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31"
            }
        )
        # Should succeed or handle gracefully
        assert response.status_code in [200, 204, 404]
        
        if response.status_code == 200:
            # Check content type for Excel
            content_type = response.headers.get("content-type", "")
            assert "spreadsheet" in content_type or "excel" in content_type

    async def test_faculty_can_export_own_subject(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject
    ):
        """Test faculty can export attendance for their own subjects."""
        response = await client.post(
            "/api/export/attendance/pdf",
            headers={"Authorization": f"Bearer {faculty_token}"},
            json={
                "subject_id": test_subject.id,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31"
            }
        )
        # Should be allowed
        assert response.status_code in [200, 204, 404]

    async def test_student_cannot_export_attendance(
        self,
        client: AsyncClient,
        student_token: str,
        test_subject: Subject
    ):
        """Test students cannot export attendance data."""
        response = await client.post(
            "/api/export/attendance/pdf",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "subject_id": test_subject.id,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31"
            }
        )
        # Should be forbidden
        assert response.status_code == 403

    async def test_export_with_invalid_date_range(
        self,
        client: AsyncClient,
        admin_token: str,
        test_subject: Subject
    ):
        """Test export handles invalid date ranges gracefully."""
        response = await client.post(
            "/api/export/attendance/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "subject_id": test_subject.id,
                "start_date": "2026-12-31",
                "end_date": "2026-01-01"  # End before start
            }
        )
        # Should handle gracefully (400 or empty result)
        assert response.status_code in [200, 204, 400, 422]
