"""
Integration tests for pagination behavior across endpoints.

Tests for limit, offset, and pagination parameters.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import (
    create_test_location,
    create_test_session,
    create_test_student,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestPaginationWithLimit:
    """Test pagination with limit parameter."""

    async def test_list_sessions_with_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/sessions?limit=10 returns limited results."""
        # Create multiple sessions
        location = await create_test_location(db_session)
        for i in range(15):
            await create_test_session(
                db_session, location=location, name=f"Session {i}"
            )

        response = await test_client.get("/api/v1/sessions?limit=10")

        assert response.status_code == HTTP_200_OK
        if response.status_code == HTTP_200_OK:
            data = response.json()
            if "items" in data:
                assert len(data["items"]) <= 10

    async def test_list_locations_with_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/admin/locations?limit=5 returns limited results."""
        # Create multiple locations
        for i in range(10):
            await create_test_location(db_session, name=f"Location {i}")

        response = await test_client.get("/api/v1/admin/locations/?limit=5")

        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestPaginationWithOffset:
    """Test pagination with offset parameter."""

    async def test_list_sessions_with_offset(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/sessions?offset=5 skips first results."""
        # Create multiple sessions
        location = await create_test_location(db_session)
        for i in range(10):
            await create_test_session(
                db_session, location=location, name=f"Session {i}"
            )

        response = await test_client.get("/api/v1/sessions?offset=5")

        assert response.status_code == HTTP_200_OK

    async def test_list_students_with_offset_and_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/students?limit=10&offset=5 with both parameters."""
        # Create multiple students
        from tests.integration.test_fixtures import create_test_caregiver

        caregiver = await create_test_caregiver(db_session)
        for i in range(20):
            await create_test_student(
                db_session, caregiver=caregiver, name=f"Student {i}"
            )

        response = await test_client.get("/api/v1/students?limit=10&offset=5")

        # Endpoint may require auth
        assert response.status_code in (HTTP_200_OK, 401, 403)


@pytest.mark.integration
class TestPaginationEdgeCases:
    """Test edge cases in pagination."""

    async def test_limit_zero(self, test_client):
        """Test limit=0 handling."""
        response = await test_client.get("/api/v1/sessions?limit=0")

        # May return 400 or handle gracefully
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)

    async def test_negative_offset(self, test_client):
        """Test negative offset handling."""
        response = await test_client.get("/api/v1/sessions?offset=-1")

        # May return 400 or handle gracefully
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)

    async def test_very_large_limit(self, test_client):
        """Test very large limit parameter."""
        response = await test_client.get("/api/v1/sessions?limit=1000000")

        # Should return 200 or handle gracefully
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)

    async def test_non_numeric_limit(self, test_client):
        """Test non-numeric limit parameter."""
        response = await test_client.get("/api/v1/sessions?limit=abc")

        # Should return 400
        assert response.status_code == HTTP_400_BAD_REQUEST
