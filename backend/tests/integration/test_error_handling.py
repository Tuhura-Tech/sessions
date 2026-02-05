"""
Integration tests for error handling across endpoints.

Tests for common error scenarios and edge cases.
"""

import pytest
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestNotFoundErrors:
    """Test 404 not found error handling."""

    async def test_get_nonexistent_session(self, test_client):
        """Test GET nonexistent session returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/sessions/{fake_id}")

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_nonexistent_student(self, test_client):
        """Test GET nonexistent student returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/students/{fake_id}")

        # May be 404 or auth error depending on auth
        assert response.status_code in (HTTP_404_NOT_FOUND, 401, 403)


@pytest.mark.integration
class TestValidationErrors:
    """Test request validation error handling."""

    async def test_invalid_email_format(self, test_client):
        """Test invalid email returns 400."""
        response = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": "not-an-email"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_missing_required_field(self, test_client):
        """Test missing required field returns 400."""
        response = await test_client.post("/api/v1/auth/magic-link", json={})

        assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestAuthenticationErrors:
    """Test authentication and authorization error handling."""

    async def test_unauthenticated_access_to_caregiver_profile(self, test_client):
        """Test unauthenticated access to caregiver profile."""
        response = await test_client.get("/api/v1/me")

        # Should require auth
        assert response.status_code in (HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN)

    async def test_invalid_session_cookie(self, test_client):
        """Test request with invalid session cookie."""
        # Make a request with fake session cookie
        test_client.cookies.set("caregiver_session", "invalid-token")
        response = await test_client.get("/api/v1/me")

        # Should return auth error
        assert response.status_code in (
            HTTP_401_UNAUTHORIZED,
            HTTP_403_FORBIDDEN,
            401,
            403,
        )


@pytest.mark.integration
class TestMethodErrors:
    """Test HTTP method errors."""

    async def test_post_to_get_endpoint(self, test_client):
        """Test POST to GET-only endpoint."""
        response = await test_client.post("/api/v1/sessions")

        # Should return method not allowed or similar error
        assert response.status_code in (405, 400, 404)

    async def test_get_to_post_endpoint(self, test_client):
        """Test GET to POST-only endpoint."""
        response = await test_client.get("/api/v1/auth/magic-link")

        # Should return method not allowed
        assert response.status_code in (405, 404)
