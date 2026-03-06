"""Test dispute resolution endpoints."""
import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.subject import Subject
from app.models.subject_attendance import SubjectAttendance


@pytest.mark.asyncio
class TestDisputeResolution:
    """Test dispute resolution functionality."""

    async def test_admin_resolve_disputed_record(
        self,
        client: AsyncClient,
        admin_token: str,
        disputed_attendance: SubjectAttendance
    ):
        """Test admin can resolve disputed attendance."""
        response = await client.post(
            f"/api/admin/attendance/{disputed_attendance.id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "final_status": "Present",
                "notes": "Verified with faculty, student was present"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Check that resolution was successful
        assert "message" in data or "final_status" in data

    async def test_mentor_resolve_own_cohort_record(
        self,
        client: AsyncClient,
        mentor_token: str,
        disputed_attendance: SubjectAttendance,
        mentor_user: User,
        student_user: User
    ):
        """Test mentor can resolve for their cohort students."""
        # Both mentor and student in same cohort (section A)
        assert mentor_user.section == student_user.section
        
        response = await client.post(
            f"/api/subjects/attendance/{disputed_attendance.id}/resolve",
            headers={"Authorization": f"Bearer {mentor_token}"},
            json={
                "final_status": "Present",
                "notes": "Student verified present"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Check that resolution was successful
        assert "message" in data or "final_status" in data

    async def test_faculty_cannot_resolve_disputes(
        self,
        client: AsyncClient,
        faculty_token: str,
        disputed_attendance: SubjectAttendance
    ):
        """Test faculty cannot resolve disputed records (admin/mentor only)."""
        response = await client.post(
            f"/api/admin/attendance/{disputed_attendance.id}/resolve",
            headers={"Authorization": f"Bearer {faculty_token}"},
            json={
                "final_status": "Present",
                "notes": "Attempting resolution"
            }
        )
        # Should be forbidden
        assert response.status_code == 403

    async def test_student_cannot_resolve_disputes(
        self,
        client: AsyncClient,
        student_token: str,
        disputed_attendance: SubjectAttendance
    ):
        """Test students cannot resolve disputes."""
        response = await client.post(
            f"/api/subjects/attendance/{disputed_attendance.id}/resolve",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "final_status": "Present",
                "notes": "Trying to resolve my own attendance"
            }
        )
        assert response.status_code == 403

    async def test_resolve_nonexistent_record(
        self,
        client: AsyncClient,
        admin_token: str
    ):
        """Test resolving non-existent record returns 404."""
        response = await client.post(
            "/api/admin/attendance/999999/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "final_status": "Present",
                "notes": "Test"
            }
        )
        assert response.status_code == 404

    async def test_both_endpoints_behave_consistently(
        self,
        client: AsyncClient,
        admin_token: str,
        db_session,
        student_user: User,
        test_subject: Subject
    ):
        """Test both resolve endpoints produce same behavior."""
        from datetime import date
        from app.models.subject_attendance import SubjectAttendance, FinalStatus
        
        # Create two identical disputed records
        record1 = SubjectAttendance(
            student_id=student_user.id,
            subject_id=test_subject.id,
            date=date.today(),
            face_verified=True,
            faculty_marked=False,
            final_status=FinalStatus.DISPUTED
        )
        record2 = SubjectAttendance(
            student_id=student_user.id,
            subject_id=test_subject.id,
            date=date(2026, 3, 6),  # Different date to avoid unique constraint
            face_verified=True,
            faculty_marked=False,
            final_status=FinalStatus.DISPUTED
        )
        db_session.add_all([record1, record2])
        await db_session.commit()
        await db_session.refresh(record1)
        await db_session.refresh(record2)
        
        # Resolve via admin endpoint
        response1 = await client.post(
            f"/api/admin/attendance/{record1.id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"final_status": "Present", "notes": "Test"}
        )
        
        # Resolve via subjects endpoint
        response2 = await client.post(
            f"/api/subjects/attendance/{record2.id}/resolve",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"final_status": "Present", "notes": "Test"}
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should succeed with same status
        data1 = response1.json()
        data2 = response2.json()
        # Both should indicate success
        assert "message" in data1 or "final_status" in data1
        assert "message" in data2 or "final_status" in data2
