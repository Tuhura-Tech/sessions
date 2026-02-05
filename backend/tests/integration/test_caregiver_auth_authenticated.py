"""Tests for caregiver authentication and signup endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestCaregiverMagicLinkEndpoint:
    """Tests for POST /api/v1/auth/magic-link endpoint."""

    async def test_request_magic_link_new_user(self, client: AsyncClient) -> None:
        """Test requesting magic link for new caregiver."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "newcaregiver@test.com"},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True

    async def test_request_magic_link_existing_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test requesting magic link for existing caregiver."""
        from app.db import models as m

        # Create caregiver
        caregiver = m.Caregiver(email="existingcaregiver@test.com", email_verified=True)
        db_session.add(caregiver)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "existingcaregiver@test.com"},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True


class TestCaregiverLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    async def test_logout_success(
        self, client: AsyncClient, caregiver_session_cookie: str
    ) -> None:
        """Test logout clears session."""
        response = await client.post(
            "/api/v1/auth/logout",
            cookies={"caregiver_session": caregiver_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True
