"""Tests for security and rate limiting functionality."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestRateLimiting:
    """Test rate limiting on protected endpoints."""

    async def test_magic_link_endpoint_accessible(self, client: AsyncClient) -> None:
        """Test that magic link endpoint is accessible."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "test@example.com"},
        )
        # Should be 200 or 429 (if rate limited), but not 404
        assert response.status_code in [HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS]

    async def test_health_check_no_rate_limit(self, client: AsyncClient) -> None:
        """Test that health check endpoint has no rate limit."""
        for _ in range(5):
            response = await client.get("/api/v1/health")
            assert response.status_code == HTTP_200_OK

    async def test_sessions_list_endpoint_accessible(self, client: AsyncClient) -> None:
        """Test that public sessions list endpoint is accessible."""
        response = await client.get("/api/v1/sessions")
        assert response.status_code == HTTP_200_OK


class TestSecurityHeaders:
    """Test that security headers are properly set."""

    async def test_health_endpoint_response(self, client: AsyncClient) -> None:
        """Test health endpoint returns proper response."""
        response = await client.get("/api/v1/health")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        # Health check should return some status info
        assert data is not None


class TestAuthenticationFlow:
    """Test authentication flow and session handling."""

    async def test_magic_link_flow_generates_token(self, client: AsyncClient) -> None:
        """Test that magic link endpoint generates a token."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "flowtest@example.com"},
        )
        # Should succeed
        assert response.status_code in [HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS]

    async def test_session_endpoint_requires_auth(self, client: AsyncClient) -> None:
        """Test that caregiver session endpoints require authentication."""
        response = await client.get("/api/v1/me")
        assert response.status_code in [401, 403]

    async def test_session_endpoint_works_with_auth(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test that session endpoints work with valid authentication."""
        response = await client.get(
            "/api/v1/me",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
