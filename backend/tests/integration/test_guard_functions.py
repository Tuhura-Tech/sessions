"""Tests for guard functions and authorization."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_200_OK

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestCaregiverGuards:
    """Test caregiver guard and authorization functions."""

    async def test_unauthorized_request_to_protected_endpoint(
        self, client: AsyncClient
    ) -> None:
        """Test that protected endpoints reject requests without valid session."""
        response = await client.get("/api/v1/me")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_authorized_request_to_protected_endpoint(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test that protected endpoints accept requests with valid session."""
        response = await client.get(
            "/api/v1/me",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

    async def test_invalid_session_token_rejected(self, client: AsyncClient) -> None:
        """Test that invalid session tokens are rejected."""
        response = await client.get(
            "/api/v1/me",
            cookies={"caregiver_session": "invalid-token-12345"},
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_student_list_requires_auth(self, client: AsyncClient) -> None:
        """Test that student list endpoint requires authentication."""
        response = await client.get("/api/v1/students")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_student_list_with_auth(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test that student list works with authentication."""
        response = await client.get(
            "/api/v1/students",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

    async def test_signups_list_requires_auth(self, client: AsyncClient) -> None:
        """Test that signups list endpoint requires authentication."""
        response = await client.get("/api/v1/signups/")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_signups_list_with_auth(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test that signups list works with authentication."""
        response = await client.get(
            "/api/v1/signups/",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        assert response.status_code == HTTP_200_OK


class TestAdminGuards:
    """Test admin guard and authorization functions."""

    async def test_admin_endpoint_requires_auth(self, client: AsyncClient) -> None:
        """Test that admin endpoints reject unauthenticated requests."""
        response = await client.get("/api/v1/admin/sessions/")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_caregiver_cannot_access_admin_endpoints(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test that caregiver sessions cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/sessions/",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        # Should be 401 or 403
        assert response.status_code in [HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN]

    async def test_invalid_admin_token_rejected(self, client: AsyncClient) -> None:
        """Test that invalid admin tokens are rejected."""
        response = await client.get(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": "invalid-token-12345"},
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_admin_endpoint_with_valid_session(
        self, admin_session_cookie: str, client: AsyncClient
    ) -> None:
        """Test that admin endpoints work with valid admin session."""
        response = await client.get(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
