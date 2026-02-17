"""
Integration tests for admin location management endpoints.

Tests location list, get, create, update, and session listings
with proper authentication, HTTP status codes, and payload validation.
"""

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from tests.integration.test_fixtures import (
    create_test_location,
    create_test_session,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminLocationList:
    """Test admin location listing."""

    async def test_list_locations_includes_created(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing locations includes created locations and total count."""
        location = await create_test_location(db_session)

        response = await client.get(
            "/api/v1/admin/locations/",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert any(item["id"] == str(location.id) for item in data["items"])
        assert data["total"] >= 1

    async def test_list_locations_without_auth(self, client: AsyncClient) -> None:
        """Test listing locations without authentication fails."""
        response = await client.get("/api/v1/admin/locations/")
        assert response.status_code in [302, 401, 403]


class TestAdminLocationCreate:
    """Test admin location creation."""

    async def test_create_location_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a new location succeeds."""
        payload = {
            "name": "New Location",
            "address": "456 New St",
            "region": "Test Region",
            "lat": -41.2865,
            "lng": 174.7762,
            "contactName": "Contact",
            "contactEmail": "contact@example.com",
        }

        response = await client.post(
            "/api/v1/admin/locations/",
            json=payload,
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Location"
        assert data["address"] == "456 New St"
        assert data["region"] == "Test Region"
        assert data.get("contactName") or data.get("contact_name") == "Contact"
        assert (
            data.get("contactEmail")
            or data.get("contact_email") == "contact@example.com"
        )
        assert "id" in data

    async def test_create_location_without_auth(self, client: AsyncClient) -> None:
        """Test creating location without authentication fails."""
        response = await client.post(
            "/api/v1/admin/locations/",
            json={
                "name": "New Location",
                "address": "456 New St",
                "region": "Test Region",
                "lat": -41.2865,
                "lng": 174.7762,
                "contactName": "Contact",
                "contactEmail": "contact@example.com",
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminLocationUpdate:
    """Test admin location updates."""

    async def test_update_location_name(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating location name returns modified data."""
        location = await create_test_location(db_session, name="Old Name")

        response = await client.patch(
            f"/api/v1/admin/locations/{location.id}",
            json={"name": "Updated Location"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == str(location.id)
        assert data["name"] == "Updated Location"

    async def test_update_location_not_found(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating nonexistent location returns 404."""
        response = await client.patch(
            f"/api/v1/admin/locations/{uuid4()}",
            json={"name": "Updated Location"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_update_location_without_auth(self, client: AsyncClient) -> None:
        """Test updating location without authentication fails."""
        response = await client.patch(
            f"/api/v1/admin/locations/{uuid4()}",
            json={"name": "Updated Location"},
        )
        assert response.status_code in [302, 401, 403]


class TestAdminLocationSessions:
    """Test location sessions listing."""

    async def test_get_location_sessions_not_found(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test getting sessions for nonexistent location returns 404."""
        response = await client.get(
            f"/api/v1/admin/locations/{uuid4()}/sessions",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_location_sessions_excludes_archived_by_default(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test default listing excludes archived sessions."""
        location = await create_test_location(db_session)
        active_session = await create_test_session(db_session, location=location)
        archived_session = await create_test_session(
            db_session, location=location, archived=True
        )

        response = await client.get(
            f"/api/v1/admin/locations/{location.id}/sessions",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        session_ids = {item["id"] for item in data["items"]}
        assert str(active_session.id) in session_ids
        assert str(archived_session.id) not in session_ids

    async def test_get_location_sessions_includes_archived_when_requested(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test include_archived=true returns archived sessions."""
        location = await create_test_location(db_session)
        archived_session = await create_test_session(
            db_session, location=location, archived=True
        )

        response = await client.get(
            f"/api/v1/admin/locations/{location.id}/sessions?include_archived=true",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        session_ids = {item["id"] for item in data["items"]}
        assert str(archived_session.id) in session_ids

    async def test_get_location_sessions_without_auth(
        self, client: AsyncClient
    ) -> None:
        """Test getting location sessions without authentication fails."""
        response = await client.get(f"/api/v1/admin/locations/{uuid4()}/sessions")
        assert response.status_code in [302, 401, 403]
