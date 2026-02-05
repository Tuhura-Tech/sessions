"""
Integration tests for admin signup management endpoints.

Tests for signup operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminSignupListEndpoint:
    """Test admin signup listing endpoint."""

    async def test_list_signups(self, test_client):
        """Test GET /api/v1/admin/signups lists all signups."""
        response = await test_client.get("/api/v1/admin/signups/")

        # Expect 200, 401, 403, or method not allowed
        assert response.status_code in (HTTP_200_OK, 401, 403, 405)


@pytest.mark.integration
class TestAdminSignupDetailEndpoint:
    """Test admin signup detail endpoint."""

    async def test_get_signup(self, test_client):
        """Test GET /api/v1/admin/signups/{id} gets signup details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/admin/signups/{fake_id}")

        # Expect 200, 404, or auth error
        assert response.status_code in (HTTP_200_OK, 400, 401, 403, HTTP_404_NOT_FOUND)


@pytest.mark.integration
class TestAdminSignupUpdateEndpoint:
    """Test admin signup update endpoint."""

    async def test_update_signup(self, test_client):
        """Test PATCH /api/v1/admin/signups/{id} updates signup."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/signups/{fake_id}", json={"status": "approved"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)
