"""Tests for admin caregiver management endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from tests.factories import CaregiverFactory

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminCaregiverManagement:
    """Test admin caregiver management endpoints."""

    async def test_list_caregivers_requires_auth(self, client: AsyncClient) -> None:
        """Test that caregiver list requires authentication."""
        response = await client.get("/api/v1/admin/caregivers/")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_list_caregivers_with_auth(
        self, admin_session_cookie: str, client: AsyncClient, db_session
    ) -> None:
        """Test listing caregivers with admin auth."""
        # Create test caregivers
        for i in range(2):
            await db_session.merge(
                CaregiverFactory.build(email=f"admin-test-{i}@example.com")
            )
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/caregivers/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        # Response can have items/results key or be a list
        assert data is not None

    async def test_get_caregiver_requires_auth(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test that getting caregiver requires authentication."""
        caregiver = await db_session.merge(CaregiverFactory.build())
        await db_session.commit()

        response = await client.get(f"/api/v1/admin/caregivers/{caregiver.id}")
        assert response.status_code == HTTP_401_UNAUTHORIZED

    async def test_get_caregiver_with_auth(
        self, admin_session_cookie: str, client: AsyncClient, db_session
    ) -> None:
        """Test getting a specific caregiver with admin auth."""
        caregiver = await db_session.merge(
            CaregiverFactory.build(
                email="get-caregiver-test@example.com",
                name="Test Caregiver Get",
            )
        )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["email"] == caregiver.email

    async def test_get_nonexistent_caregiver(
        self, admin_session_cookie: str, client: AsyncClient
    ) -> None:
        """Test getting non-existent caregiver returns 404."""
        response = await client.get(
            "/api/v1/admin/caregivers/nonexistent-id",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
