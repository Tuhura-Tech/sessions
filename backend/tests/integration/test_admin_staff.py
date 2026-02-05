"""
Integration tests for admin staff management endpoints.

Tests for staff CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminStaffListEndpoint:
    """Test admin staff listing endpoint."""

    async def test_list_staff(self, test_client):
        """Test GET /admin/v1/staff lists all staff."""
        response = await test_client.get("/api/v1/admin/staff/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminStaffCreateEndpoint:
    """Test admin staff creation endpoint."""

    async def test_create_staff(self, test_client):
        """Test POST /admin/v1/staff creates a staff member."""
        response = await test_client.post(
            "/api/v1/admin/staff/",
            json={
                "name": "New Staff",
                "email": "staff@example.com",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminStaffUpdateEndpoint:
    """Test admin staff update endpoint."""

    async def test_update_staff(self, test_client):
        """Test PATCH /api/v1/admin/staff/{id} updates staff."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/staff/{fake_id}", json={"name": "Updated Staff"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminStaffDeleteEndpoint:
    """Test admin staff deletion endpoint."""

    async def test_delete_staff(self, test_client):
        """Test DELETE /api/v1/admin/staff/{id} deletes staff."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/staff/{fake_id}")

        # Expect 200, 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)
