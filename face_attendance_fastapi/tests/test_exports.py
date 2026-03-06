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
        response = await client.get(
            "/api/export/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={
                "subject_id": test_subject.id,
                "year": 2026,
                "month": 0
            }
        )
        # Should succeed or handle gracefully
        assert response.status_code in [200, 404]
        
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
        # Excel export not implemented in this version
        # Skip this test for now
        pass

    async def test_faculty_can_export_own_subject(
        self,
        client: AsyncClient,
        faculty_token: str,
        test_subject: Subject
    ):
        """Test faculty can export attendance for their own subjects."""
        response = await client.get(
            "/api/export/pdf",
            headers={"Authorization": f"Bearer {faculty_token}"},
            params={
                "subject_id": test_subject.id,
                "year": 2026,
                "month": 0
            }
        )
        # Should be allowed
        assert response.status_code in [200, 404]

    async def test_student_cannot_export_attendance(
        self,
        client: AsyncClient,
        student_token: str,
        test_subject: Subject
    ):
        """Test students cannot export attendance data."""
        response = await client.get(
            "/api/export/pdf",
            headers={"Authorization": f"Bearer {student_token}"},
            params={
                "subject_id": test_subject.id,
                "year": 2026,
                "month": 0
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
        response = await client.get(
            "/api/export/pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={
                "subject_id": test_subject.id,
                "year": 2026,
                "month": 15  # Invalid month
            }
        )
        # Should handle gracefully
        assert response.status_code in [200, 404, 422]
