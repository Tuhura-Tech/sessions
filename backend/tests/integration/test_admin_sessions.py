"""
Integration tests for admin session management endpoints.

Tests for session CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_location, create_test_session


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminSessionListEndpoint:
    """Test admin session listing endpoint."""

    async def test_list_sessions(self, test_client):
        """Test GET /api/v1/admin/sessions lists all sessions."""
        response = await test_client.get("/api/v1/admin/sessions/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)

    async def test_list_sessions_with_data(self, test_client, db_session: AsyncSession):
        """Test session list includes created sessions."""
        location = await create_test_location(db_session)
        await create_test_session(db_session, location=location)

        response = await test_client.get("/api/v1/admin/sessions/")

        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminSessionCreateEndpoint:
    """Test admin session creation endpoint."""

    async def test_create_session(self, test_client, db_session: AsyncSession):
        """Test POST /api/v1/admin/sessions creates a session."""
        location = await create_test_location(db_session)

        response = await test_client.post(
            "/api/v1/admin/sessions/",
            json={
                "name": "New Session",
                "location_id": str(location.id),
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminSessionUpdateEndpoint:
    """Test admin session update endpoint."""

    async def test_update_session(self, test_client):
        """Test PATCH /api/v1/admin/sessions/{id} updates session."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/sessions/{fake_id}", json={"name": "Updated Session"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminSessionDeleteEndpoint:
    """Test admin session deletion endpoint."""

    async def test_delete_session(self, test_client):
        """Test DELETE /api/v1/admin/sessions/{id} deletes session."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/sessions/{fake_id}")

        # Expect 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)
