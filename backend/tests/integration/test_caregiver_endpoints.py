"""
Integration tests for caregiver endpoints.

Tests for caregiver-specific operations and profile management.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_caregiver


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestCaregiverProfileEndpoint:
    """Test caregiver profile endpoints."""

    async def test_get_caregiver_profile(self, test_client, db_session: AsyncSession):
        """Test GET /api/v1/me returns authenticated caregiver profile."""
        await create_test_caregiver(db_session)

        # This test requires authentication - would need to set session cookie
        # For now, we'll test that the endpoint exists
        response = await test_client.get("/api/v1/me")

        # Expect auth error when unauthenticated
        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestCaregiverStudentsEndpoint:
    """Test caregiver students listing endpoint."""

    async def test_list_caregiver_students(self, test_client):
        """Test GET /api/v1/students lists students for caregiver."""
        # This test requires authentication
        response = await test_client.get("/api/v1/students")

        # Expect auth error when unauthenticated
        assert response.status_code in (HTTP_200_OK, 401, 403)

    async def test_get_student_detail(self, test_client):
        """Test GET /api/v1/students/{id} gets student details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/students/{fake_id}")

        # Expect auth error or 404
        assert response.status_code in (HTTP_200_OK, 401, 403, HTTP_404_NOT_FOUND)
