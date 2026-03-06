"""Test authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication flow."""

    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint is accessible."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_login_success(self, client: AsyncClient, admin_user):
        """Test successful login returns JWT token."""
        response = await client.post(
            "/api/auth/login",
            data={"username": "admin@test.com", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient, admin_user):
        """Test login fails with invalid credentials."""
        response = await client.post(
            "/api/auth/login",
            data={"username": "admin@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for non-existent user."""
        response = await client.post(
            "/api/auth/login",
            data={"username": "nobody@test.com", "password": "password"}
        )
        assert response.status_code == 401

    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test protected endpoint rejects requests without token."""
        response = await client.get("/api/subjects/")
        assert response.status_code == 401

    async def test_protected_endpoint_with_token(
        self, 
        client: AsyncClient, 
        admin_token: str
    ):
        """Test protected endpoint accepts valid token."""
        response = await client.get(
            "/api/subjects/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test protected endpoint rejects invalid token."""
        response = await client.get(
            "/api/subjects/",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

    async def test_get_current_user(
        self, 
        client: AsyncClient, 
        admin_token: str,
        admin_user
    ):
        """Test retrieving current user data."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_user.email
        assert data["role"] == "Admin"
