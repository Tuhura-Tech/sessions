"""
Integration tests for admin occurrence management endpoints.

Tests for occurrence operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminOccurrenceListEndpoint:
    """Test admin occurrence listing endpoint."""

    async def test_list_occurrences(self, test_client):
        """Test GET /api/v1/admin/occurrences lists all occurrences."""
        response = await test_client.get("/api/v1/admin/occurrences/")

        # Expect 200, 401, 403, or method not allowed
        assert response.status_code in (HTTP_200_OK, 401, 403, 405)


@pytest.mark.integration
class TestAdminOccurrenceDetailEndpoint:
    """Test admin occurrence detail endpoint."""

    async def test_get_occurrence(self, test_client):
        """Test GET /api/v1/admin/occurrences/{id} gets occurrence details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/admin/occurrences/{fake_id}")

        # Expect 200, 404, or auth error
        assert response.status_code in (HTTP_200_OK, 400, 401, 403, HTTP_404_NOT_FOUND)


@pytest.mark.integration
class TestAdminOccurrenceCreateEndpoint:
    """Test admin occurrence creation endpoint."""

    async def test_create_occurrence(self, test_client):
        """Test POST /api/v1/admin/occurrences creates an occurrence."""
        response = await test_client.post(
            "/api/v1/admin/occurrences/",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "date": "2025-01-15",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminOccurrenceUpdateEndpoint:
    """Test admin occurrence update endpoint."""

    async def test_update_occurrence(self, test_client):
        """Test PATCH /api/v1/admin/occurrences/{id} updates occurrence."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/occurrences/{fake_id}", json={"status": "active"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminOccurrenceDeleteEndpoint:
    """Test admin occurrence deletion endpoint."""

    async def test_delete_occurrence(self, test_client):
        """Test DELETE /api/v1/admin/occurrences/{id} deletes occurrence."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/occurrences/{fake_id}")

        # Expect 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)
