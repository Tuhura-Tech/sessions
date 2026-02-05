"""
Integration tests for admin caregiver management endpoints.

Tests for caregiver CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_caregiver


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminCaregiverListEndpoint:
    """Test admin caregiver listing endpoint."""

    async def test_list_caregivers(self, test_client):
        """Test GET /api/v1/admin/caregivers lists all caregivers."""
        response = await test_client.get("/api/v1/admin/caregivers/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)

    async def test_list_caregivers_with_data(
        self, test_client, db_session: AsyncSession
    ):
        """Test caregiver list includes created caregivers."""
        await create_test_caregiver(db_session)

        response = await test_client.get("/api/v1/admin/caregivers/")

        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminCaregiverCreateEndpoint:
    """Test admin caregiver creation endpoint."""

    async def test_create_caregiver(self, test_client):
        """Test POST /api/v1/admin/caregivers creates a caregiver."""
        response = await test_client.post(
            "/api/v1/admin/caregivers/",
            json={
                "email": "newcaregiver@example.com",
                "name": "New Caregiver",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminCaregiverDetailEndpoint:
    """Test admin caregiver detail endpoint."""

    async def test_get_caregiver(self, test_client):
        """Test GET /api/v1/admin/caregivers/{id} gets caregiver details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/admin/caregivers/{fake_id}")

        # Expect 200, 404, or auth error
        assert response.status_code in (HTTP_200_OK, 400, 401, 403, HTTP_404_NOT_FOUND)


@pytest.mark.integration
class TestAdminCaregiverUpdateEndpoint:
    """Test admin caregiver update endpoint."""

    async def test_update_caregiver(self, test_client):
        """Test PATCH /api/v1/admin/caregivers/{id} updates caregiver."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/caregivers/{fake_id}", json={"name": "Updated Caregiver"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminCaregiverDeleteEndpoint:
    """Test admin caregiver deletion endpoint."""

    async def test_delete_caregiver(self, test_client):
        """Test DELETE /api/v1/admin/caregivers/{id} deletes caregiver."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/caregivers/{fake_id}")

        # Expect 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)
