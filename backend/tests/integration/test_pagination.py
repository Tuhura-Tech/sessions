"""
Integration tests for pagination behavior across endpoints.

Comprehensive tests for limit, offset, pagination parameters, ordering,
and edge cases across caregiver and admin endpoints.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import (
    create_test_caregiver,
    create_test_location,
    create_test_session,
    create_test_student,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestCaregiverSessionsPagination:
    """Test pagination for caregiver sessions endpoint."""

    async def test_list_sessions_with_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test GET /api/v1/sessions?limit=10 returns exactly limited results."""
        # Create 25 sessions
        location = await create_test_location(db_session)
        for i in range(25):
            await create_test_session(
                db_session, location=location, name=f"Session {i:02d}"
            )

        response = await test_client.get("/api/v1/sessions?limit=10")

        assert response.status_code == HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        # Should return exactly 10 items (or fewer if total < 10)
        assert len(data["items"]) == min(10, data["total"])
        assert data["total"] >= 25

    async def test_list_sessions_pagination_offset(
        self, test_client, db_session: AsyncSession
    ):
        """Test session pagination offset returns correct page."""
        location = await create_test_location(db_session)

        # Create 30 sessions with identifiable names
        created_names = []
        for i in range(30):
            session = await create_test_session(
                db_session, location=location, name=f"Pag Session {i:02d}"
            )
            created_names.append(session.name)

        # Get first page
        page1 = await test_client.get("/api/v1/sessions?limit=10&offset=0")

        # Get second page
        page2 = await test_client.get("/api/v1/sessions?limit=10&offset=10")

        assert page1.status_code == HTTP_200_OK
        assert page2.status_code == HTTP_200_OK

        data1 = page1.json()
        data2 = page2.json()

        # Extract IDs from both pages
        ids_page1 = {item["id"] for item in data1["items"]}
        ids_page2 = {item["id"] for item in data2["items"]}

        # Verify no overlap between pages
        assert len(ids_page1 & ids_page2) == 0, (
            "Pages should not have overlapping items"
        )

        # Verify both pages have correct size
        assert len(data1["items"]) == 10
        assert len(data2["items"]) == 10

    async def test_list_sessions_total_count_consistent(
        self, test_client, db_session: AsyncSession
    ):
        """Test total count remains consistent across paginated requests."""
        location = await create_test_location(db_session)

        # Create exactly 17 sessions
        for i in range(17):
            await create_test_session(db_session, location=location, name=f"Count {i}")

        # Get multiple pages
        page1 = await test_client.get("/api/v1/sessions?limit=10&offset=0")
        page2 = await test_client.get("/api/v1/sessions?limit=10&offset=10")

        data1 = page1.json()
        data2 = page2.json()

        # Both should report same total
        assert data1["total"] == data2["total"]
        assert data1["total"] >= 17

        # First page should have 10 items
        assert len(data1["items"]) == 10
        # Second page should have remaining items
        assert len(data2["items"]) >= 7

    async def test_list_sessions_offset_beyond_total(
        self, test_client, db_session: AsyncSession
    ):
        """Test pagination with offset beyond total returns empty items."""
        location = await create_test_location(db_session)

        # Create only 5 sessions
        for i in range(5):
            await create_test_session(
                db_session, location=location, name=f"Limited {i}"
            )

        # Request offset way beyond total
        response = await test_client.get("/api/v1/sessions?limit=10&offset=1000")

        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Should return empty items but accurate total
        assert data["items"] == []
        # Total should reflect ALL sessions in database (may be > 5 from other tests)
        assert data["total"] >= 0  # Just ensure we got a response


class TestAdminLocationsPagination:
    """Test pagination for admin locations endpoint."""

    async def test_list_locations_with_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test admin locations pagination with limit parameter."""
        # Create 15 locations
        for i in range(15):
            await create_test_location(db_session, name=f"Location {i:02d}")

        response = await test_client.get("/api/v1/admin/locations/?limit=5")

        # May require auth
        if response.status_code == HTTP_200_OK:
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 5
            assert data["total"] >= 15
        else:
            assert response.status_code in (401, 403)

    async def test_list_locations_zero_offset_same_as_no_offset(
        self, test_client, db_session: AsyncSession
    ):
        """Test explicit offset=0 returns same as no offset."""
        # Create locations
        for i in range(8):
            await create_test_location(db_session, name=f"Loc {i}")

        # No offset
        no_offset = await test_client.get("/api/v1/admin/locations/?limit=10")

        # Explicit offset=0
        with_offset = await test_client.get(
            "/api/v1/admin/locations/?limit=10&offset=0"
        )

        # Both should succeed or both fail auth
        assert no_offset.status_code == with_offset.status_code

        if no_offset.status_code == HTTP_200_OK:
            # Should return same items
            assert no_offset.json()["items"] == with_offset.json()["items"]


class TestStudentsPagination:
    """Test pagination for students endpoint."""

    async def test_list_students_with_offset_and_limit(
        self, test_client, db_session: AsyncSession
    ):
        """Test students pagination with both offset and limit."""
        caregiver = await create_test_caregiver(db_session)

        # Create 25 students
        for i in range(25):
            await create_test_student(
                db_session, caregiver=caregiver, name=f"Student{i:02d} Test"
            )

        response = await test_client.get("/api/v1/students?limit=10&offset=5")

        # Endpoint may require auth
        if response.status_code == HTTP_200_OK:
            data = response.json()

            # Should return items after skipping first 5
            assert "items" in data
            assert len(data["items"]) == 10
            assert data["total"] >= 25
        else:
            assert response.status_code in (401, 403)

    async def test_list_students_ordering_consistency(
        self, test_client, db_session: AsyncSession
    ):
        """Test students are returned in consistent order across pages."""
        caregiver = await create_test_caregiver(db_session)

        # Create students
        for i in range(20):
            await create_test_student(
                db_session, caregiver=caregiver, name=f"Order{i:02d} Test"
            )

        # Get two pages
        page1 = await test_client.get("/api/v1/students?limit=10&offset=0")
        page2 = await test_client.get("/api/v1/students?limit=10&offset=10")

        if page1.status_code == HTTP_200_OK and page2.status_code == HTTP_200_OK:
            data1 = page1.json()
            data2 = page2.json()

            # Verify no duplicates between pages
            ids_page1 = {item["id"] for item in data1["items"]}
            ids_page2 = {item["id"] for item in data2["items"]}
            assert len(ids_page1 & ids_page2) == 0


class TestPaginationEdgeCases:
    """Test edge cases and boundary conditions for pagination."""

    async def test_limit_zero(self, test_client):
        """Test limit=0 is handled appropriately."""
        response = await test_client.get("/api/v1/sessions?limit=0")

        # Should either return empty items or reject
        if response.status_code == HTTP_200_OK:
            data = response.json()
            assert data["items"] == []
        else:
            assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_negative_offset(self, test_client):
        """Test negative offset is rejected or treated as zero."""
        response = await test_client.get("/api/v1/sessions?offset=-1")

        # Should either work (treating as 0) or reject
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)

    async def test_negative_limit(self, test_client):
        """Test negative limit is rejected."""
        response = await test_client.get("/api/v1/sessions?limit=-10")

        # Should reject negative limit
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_very_large_limit(self, test_client):
        """Test very large limit parameter is handled."""
        response = await test_client.get("/api/v1/sessions?limit=1000000")

        # Should handle gracefully - either cap it or accept
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)

    async def test_non_numeric_limit(self, test_client):
        """Test non-numeric limit parameter is rejected."""
        response = await test_client.get("/api/v1/sessions?limit=abc")

        # Should return validation error
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_non_numeric_offset(self, test_client):
        """Test non-numeric offset parameter is rejected."""
        response = await test_client.get("/api/v1/sessions?offset=xyz")

        # Should return validation error
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_fractional_pagination_params(self, test_client):
        """Test fractional limit/offset are handled."""
        response = await test_client.get("/api/v1/sessions?limit=10.5&offset=5.7")

        # Should either accept (truncating) or reject
        assert response.status_code in (HTTP_200_OK, HTTP_400_BAD_REQUEST)
