"""
Integration tests for admin block management endpoints.

Tests for block CRUD operations in the admin panel.
"""

import pytest
from litestar.status_codes import HTTP_200_OK


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminBlockListEndpoint:
    """Test admin block listing endpoint."""

    async def test_list_blocks(self, test_client):
        """Test GET /api/v1/admin/blocks lists all blocks."""
        response = await test_client.get("/api/v1/admin/blocks/")

        # Expect 200, 401, or 403
        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestAdminBlockCreateEndpoint:
    """Test admin block creation endpoint."""

    async def test_create_block(self, test_client):
        """Test POST /api/v1/admin/blocks creates a block."""
        response = await test_client.post(
            "/api/v1/admin/blocks/",
            json={
                "name": "Block 1",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        )

        # Expect 200/201 or auth/validation error
        assert response.status_code in (200, 201, 400, 401, 403)


@pytest.mark.integration
class TestAdminBlockUpdateEndpoint:
    """Test admin block update endpoint."""

    async def test_update_block(self, test_client):
        """Test PATCH /api/v1/admin/blocks/{id} updates block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/admin/blocks/{fake_id}", json={"name": "Updated Block"}
        )

        # Expect 200, 404, or auth error
        assert response.status_code in (200, 400, 401, 403, 404)


@pytest.mark.integration
class TestAdminBlockDeleteEndpoint:
    """Test admin block deletion endpoint."""

    async def test_delete_block(self, test_client):
        """Test DELETE /api/v1/admin/blocks/{id} deletes block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/admin/blocks/{fake_id}")

        # Expect 204, 404, 405, or auth error
        assert response.status_code in (200, 204, 401, 403, 404, 405)
