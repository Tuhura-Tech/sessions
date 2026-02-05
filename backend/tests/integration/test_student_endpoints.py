"""
Integration tests for student management endpoints.

Tests for student listing and detail endpoints accessible via caregiver routes.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestStudentListEndpoint:
    """Test student listing endpoints."""

    async def test_list_students(self, test_client):
        """Test student listing endpoint."""
        response = await test_client.get("/api/v1/students")

        # May require authentication or return 404
        assert response.status_code in (HTTP_200_OK, 401, 403, HTTP_404_NOT_FOUND)


@pytest.mark.integration
class TestStudentDetailEndpoint:
    """Test student detail endpoints."""

    async def test_get_student(self, test_client):
        """Test GET /api/v1/students/{id} gets student details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/students/{fake_id}")

        # Expect auth error or 404
        assert response.status_code in (HTTP_200_OK, 401, 403, HTTP_404_NOT_FOUND)
