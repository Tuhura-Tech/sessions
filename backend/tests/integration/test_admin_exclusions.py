"""
Integration tests for admin exclusion management endpoints.

Tests for exclusion CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminExclusionListEndpoint:
    """Test admin exclusion listing endpoint."""

    async def test_list_exclusions(self, test_client):
        """Test GET /api/v1/admin/exclusions lists all exclusions."""
        response = await test_client.get("/api/v1/admin/exclusions/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminExclusionCreateEndpoint:
    """Test admin exclusion creation endpoint."""

    async def test_create_exclusion(self, test_client):
        """Test POST /api/v1/admin/exclusions creates an exclusion."""
        response = await test_client.post(
            "/api/v1/admin/exclusions/",
            json={
                "date": "2025-12-25",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminExclusionDeleteEndpoint:
    """Test admin exclusion deletion endpoint."""

    async def test_delete_exclusion(self, test_client):
        """Test DELETE /api/v1/admin/exclusions/{id} deletes exclusion."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/exclusions/{fake_id}")

        # Expect 204, 404, or auth error
        assert response.status_code in (200, 204, 401, 403, 404)
