"""
Integration tests for admin exclusion management endpoints.

Tests for exclusion date CRUD operations with proper authentication and data verification.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_exclusion_date

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminExclusionList:
    """Test admin exclusion listing endpoint."""

    async def test_list_exclusions_empty(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test listing exclusion dates when none exist."""
        response = await client.get(
            "/api/v1/admin/exclusions/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

    async def test_list_exclusions_with_data(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing exclusion dates returns all created dates."""
        await create_test_exclusion_date(db_session, date=date(2025, 12, 25))
        await create_test_exclusion_date(db_session, date=date(2025, 1, 1))

        response = await client.get(
            "/api/v1/admin/exclusions/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 2

    async def test_list_exclusions_without_auth(self, client: AsyncClient) -> None:
        """Test listing exclusion dates without authentication fails."""
        response = await client.get("/api/v1/admin/exclusions/")
        assert response.status_code in [302, 401, 403]


class TestAdminExclusionCreate:
    """Test admin exclusion date creation endpoint."""

    async def test_create_exclusion_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a new exclusion date succeeds."""
        response = await client.post(
            "/api/v1/admin/exclusions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "year": 2025,
                "date": "2025-12-25",
                "reason": "Christmas",
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["date"] == "2025-12-25"
        assert "id" in data

    async def test_create_exclusion_without_auth(self, client: AsyncClient) -> None:
        """Test creating exclusion date without authentication fails."""
        response = await client.post(
            "/api/v1/admin/exclusions/",
            json={
                "date": "2025-12-25",
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminExclusionGet:
    """Test retrieving a specific exclusion date."""

    async def test_get_exclusion(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving an exclusion date by ID."""
        exclusion = await create_test_exclusion_date(db_session, date=date(2025, 6, 15))

        response = await client.get(
            f"/api/v1/admin/exclusions/{exclusion.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["date"] == "2025-06-15"
        assert str(data["id"]) == str(exclusion.id)

    async def test_get_nonexistent_exclusion(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent exclusion date returns 404."""
        response = await client.get(
            "/api/v1/admin/exclusions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminExclusionUpdate:
    """Test updating an exclusion date."""

    async def test_update_exclusion_date(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating exclusion date succeeds."""
        exclusion = await create_test_exclusion_date(db_session, date=date(2025, 3, 15))

        response = await client.patch(
            f"/api/v1/admin/exclusions/{exclusion.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"date": "2025-03-20"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["date"] == "2025-03-20"

    async def test_update_nonexistent_exclusion(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent exclusion date returns 404."""
        response = await client.patch(
            "/api/v1/admin/exclusions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
            json={"date": "2025-03-20"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminExclusionDelete:
    """Test deleting an exclusion date."""

    async def test_delete_exclusion(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test deleting an exclusion date succeeds."""
        exclusion = await create_test_exclusion_date(
            db_session, date=date(2025, 11, 11)
        )

        response = await client.delete(
            f"/api/v1/admin/exclusions/{exclusion.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_204_NO_CONTENT

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/admin/exclusions/{exclusion.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert get_response.status_code == HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_exclusion(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test deleting non-existent exclusion date returns 404."""
        response = await client.delete(
            "/api/v1/admin/exclusions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
