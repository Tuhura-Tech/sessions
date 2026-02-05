"""Tests for admin authentication endpoints with authentication."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminAuthMeEndpoint:
    """Tests for /api/v1/admin/auth/me endpoint."""

    async def test_me_without_session(self, client: AsyncClient) -> None:
        """Test /me endpoint without authentication."""
        response = await client.get("/api/v1/admin/auth/me")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["hasSession"] is False

    async def test_me_with_session(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test /me endpoint with valid admin session."""
        response = await client.get(
            "/api/v1/admin/auth/me", cookies={"admin_session": admin_session_cookie}
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["hasSession"] is True
        assert "email" in data
        assert data["email"] == "admin@test.com"
        assert data["provider"] == "debugtoken"


class TestAdminAuthLogoutEndpoint:
    """Tests for /api/v1/admin/auth/logout endpoint."""

    async def test_logout_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test logout clears session cookie."""
        response = await client.post(
            "/api/v1/admin/auth/logout",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True
        # Verify cookie is cleared (set-cookie header with expired date)
        set_cookie = response.headers.get("set-cookie", "")
        assert "admin_session" in set_cookie.lower()
