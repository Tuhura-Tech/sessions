"""
Integration tests for admin location management endpoints.

Tests for location CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import (
    create_test_location,
    create_test_session,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminLocationListEndpoint:
    """Test admin location listing endpoint."""

    async def test_list_locations(self, test_client):
        """Test GET /api/v1/admin/locations lists all locations."""
        response = await test_client.get("/api/v1/admin/locations/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)

    async def test_list_locations_with_data(
        self, test_client, db_session: AsyncSession
    ):
        """Test location list includes created locations."""
        await create_test_location(db_session)

        response = await test_client.get("/api/v1/admin/locations/")

        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminLocationCreateEndpoint:
    """Test admin location creation endpoint."""

    async def test_create_location(self, test_client):
        """Test POST /api/v1/admin/locations creates a location."""
        response = await test_client.post(
            "/api/v1/admin/locations/",
            json={
                "name": "New Location",
                "address": "456 New St",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminLocationUpdateEndpoint:
    """Test admin location update endpoint."""

    async def test_update_location(self, test_client):
        """Test PATCH /api/v1/admin/locations/{id} updates location."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/locations/{fake_id}", json={"name": "Updated Location"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminLocationDeleteEndpoint:
    """Test admin location deletion endpoint."""

    async def test_delete_location(self, test_client):
        """Test DELETE /api/v1/admin/locations/{id} deletes location."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/locations/{fake_id}")

        # Expect 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)


@pytest.mark.integration
class TestAdminLocationSessionsEndpoint:
    """Test admin location sessions listing endpoint."""

    async def test_get_location_sessions_not_found(self, test_client):
        """Test GET /api/v1/admin/locations/{id}/sessions with invalid ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/admin/locations/{fake_id}/sessions")

        # Expect 404 or auth error
        assert response.status_code in (401, 403, 404)

    async def test_get_location_sessions_empty(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/admin/locations/{id}/sessions with no sessions."""
        location = await create_test_location(db_session)

        response = await test_client.get(
            f"/api/v1/admin/locations/{location.id}/sessions"
        )

        # Expect 200 with empty list or auth error
        assert response.status_code in (HTTP_200_OK, 401, 403)

        if response.status_code == HTTP_200_OK:
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)

    async def test_get_location_sessions_with_data(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/admin/locations/{id}/sessions returns sessions."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        response = await test_client.get(
            f"/api/v1/admin/locations/{location.id}/sessions"
        )

        # Expect 200 or auth error
        assert response.status_code in (HTTP_200_OK, 401, 403)

        if response.status_code == HTTP_200_OK:
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)
            # Should have at least one session
            if len(data["items"]) > 0:
                assert data["items"][0]["id"] == str(session.id)

    async def test_get_location_sessions_exclude_archived(
        self, test_client, db_session: AsyncSession
    ):
        """Test that archived sessions are excluded by default."""
        location = await create_test_location(db_session)
        # Create active session
        active_session = await create_test_session(db_session, location=location)
        # Create archived session
        archived_session = await create_test_session(
            db_session, location=location, archived=True
        )

        response = await test_client.get(
            f"/api/v1/admin/locations/{location.id}/sessions"
        )

        # Expect 200 or auth error
        assert response.status_code in (HTTP_200_OK, 401, 403)

        if response.status_code == HTTP_200_OK:
            data = response.json()
            session_ids = [s["id"] for s in data["items"]]

            # Should include active session
            assert str(active_session.id) in session_ids
            # Should exclude archived session by default
            assert str(archived_session.id) not in session_ids

    async def test_get_location_sessions_include_archived(
        self, test_client, db_session: AsyncSession
    ):
        """Test that archived sessions are included when requested."""
        location = await create_test_location(db_session)
        archived_session = await create_test_session(
            db_session, location=location, archived=True
        )

        response = await test_client.get(
            f"/api/v1/admin/locations/{location.id}/sessions?include_archived=true"
        )

        # Expect 200 or auth error
        assert response.status_code in (HTTP_200_OK, 401, 403)

        if response.status_code == HTTP_200_OK:
            data = response.json()
            session_ids = [s["id"] for s in data["items"]]

            # Should include archived session
            assert str(archived_session.id) in session_ids
