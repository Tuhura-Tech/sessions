"""
Integration tests for admin session management endpoints.

Tests for session CRUD operations with proper authentication and data verification.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import (
    create_test_block,
    create_test_location,
    create_test_session,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminSessionList:
    """Test admin session listing endpoint."""

    async def test_list_sessions_empty(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test listing sessions when none exist."""
        response = await client.get(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data or isinstance(data, list)

    async def test_list_sessions_with_data(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing sessions returns all created sessions."""
        location = await create_test_location(db_session, name="Test Location")
        session1 = await create_test_session(
            db_session, location=location, name="Session 1"
        )
        session2 = await create_test_session(
            db_session, location=location, name="Session 2"
        )

        response = await client.get(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 2

        names = [item.get("name") for item in items]
        assert session1.name in names
        assert session2.name in names

    async def test_list_sessions_without_auth(self, client: AsyncClient) -> None:
        """Test listing sessions without authentication fails."""
        response = await client.get("/api/v1/admin/sessions/")
        assert response.status_code in [302, 401, 403]


class TestAdminSessionCreate:
    """Test admin session creation endpoint."""

    async def test_create_session_success(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating a new session with all required fields."""
        location = await create_test_location(db_session)
        block = await create_test_block(db_session, year=2025, name="Block 1")

        response = await client.post(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "New Session",
                "sessionType": "term",
                "year": 2025,
                "dayOfWeek": 1,
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "ageLower": 5,
                "ageUpper": 8,
                "capacity": 15,
                "locationId": str(location.id),
                "blocks": [str(block.id)],
                "description": "Hands-on robotics and maker activities",
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Session"
        assert data["capacity"] == 15
        assert data["year"] == 2025
        assert data["description"] == "Hands-on robotics and maker activities"
        assert "whatToBring" not in data
        assert "prerequisites" not in data
        assert "id" in data

    async def test_create_session_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating a session without authentication fails."""
        location = await create_test_location(db_session)
        response = await client.post(
            "/api/v1/admin/sessions/",
            json={
                "name": "New Session",
                "locationId": str(location.id),
            },
        )
        assert response.status_code in [302, 401, 403]

    async def test_create_term_session_generates_occurrences(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test that creating a term session auto-generates occurrences for each block week."""
        location = await create_test_location(db_session)
        # Block spans Jan 15 – Mar 31 2025; there are 11 Mondays in that range
        block = await create_test_block(
            db_session,
            year=2025,
            name="Term Block",
            start_date=date(2025, 1, 15),
            end_date=date(2025, 3, 31),
        )

        response = await client.post(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "Term Session",
                "sessionType": "term",
                "year": 2025,
                "dayOfWeek": 1,  # Monday
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "ageLower": 5,
                "ageUpper": 12,
                "capacity": 20,
                "locationId": str(location.id),
                "blocks": [str(block.id)],
            },
        )

        assert response.status_code == HTTP_201_CREATED
        session_id = response.json()["id"]

        occ_response = await client.get(
            f"/api/v1/admin/sessions/{session_id}/occurrences",
            cookies={"admin_session": admin_session_cookie},
        )
        assert occ_response.status_code == HTTP_200_OK
        data = occ_response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) > 0, "Term session should have generated occurrences"

    async def test_create_term_session_can_skip_auto_generated_occurrences(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test that term sessions can opt out of automatic occurrence generation."""
        location = await create_test_location(db_session)
        block = await create_test_block(
            db_session,
            year=2025,
            name="Manual Occurrence Block",
            start_date=date(2025, 1, 15),
            end_date=date(2025, 3, 31),
        )

        response = await client.post(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "Manual Occurrence Session",
                "sessionType": "term",
                "year": 2025,
                "dayOfWeek": 1,
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "ageLower": 5,
                "ageUpper": 12,
                "capacity": 20,
                "locationId": str(location.id),
                "blocks": [str(block.id)],
                "generateOccurrences": False,
            },
        )

        assert response.status_code == HTTP_201_CREATED
        session_id = response.json()["id"]

        occ_response = await client.get(
            f"/api/v1/admin/sessions/{session_id}/occurrences",
            cookies={"admin_session": admin_session_cookie},
        )
        assert occ_response.status_code == HTTP_200_OK
        data = occ_response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert items == []

    async def test_create_term_session_requires_day_of_week(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Term sessions must include dayOfWeek."""
        location = await create_test_location(db_session)
        block = await create_test_block(db_session, year=2025, name="Term Block")

        response = await client.post(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "Invalid Term Session",
                "sessionType": "term",
                "year": 2025,
                "dayOfWeek": None,
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "ageLower": 5,
                "ageUpper": 12,
                "capacity": 20,
                "locationId": str(location.id),
                "blocks": [str(block.id)],
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_create_special_session_no_occurrences(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test that creating a special session does NOT auto-generate occurrences."""
        location = await create_test_location(db_session)
        block = await create_test_block(db_session, year=2025, name="Special Block")

        response = await client.post(
            "/api/v1/admin/sessions/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "Special Session",
                "sessionType": "special",
                "year": 2025,
                "dayOfWeek": None,
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "ageLower": 5,
                "ageUpper": 12,
                "capacity": 20,
                "locationId": str(location.id),
                "blocks": [str(block.id)],
            },
        )

        assert response.status_code == HTTP_201_CREATED
        session_id = response.json()["id"]

        occ_response = await client.get(
            f"/api/v1/admin/sessions/{session_id}/occurrences",
            cookies={"admin_session": admin_session_cookie},
        )
        assert occ_response.status_code == HTTP_200_OK
        data = occ_response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) == 0, (
            "Special session must not have auto-generated occurrences"
        )


class TestAdminSessionGet:
    """Test retrieving a specific session."""

    async def test_get_session(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving a session by ID returns all fields."""
        location = await create_test_location(db_session)
        session = await create_test_session(
            db_session, location=location, name="Get Test Session"
        )

        response = await client.get(
            f"/api/v1/admin/sessions/{session.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Get Test Session"
        assert str(data["id"]) == str(session.id)
        assert data["year"] == session.year
        assert "capacity" in data

    async def test_get_nonexistent_session(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent session returns 404."""
        response = await client.get(
            "/api/v1/admin/sessions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminSessionUpdate:
    """Test updating a session."""

    async def test_update_session_name(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating session name succeeds."""
        location = await create_test_location(db_session)
        session = await create_test_session(
            db_session, location=location, name="Original Name"
        )

        response = await client.patch(
            f"/api/v1/admin/sessions/{session.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated Name", "description": "Updated description"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    async def test_update_session_capacity(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating session capacity succeeds."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location, capacity=20)

        response = await client.patch(
            f"/api/v1/admin/sessions/{session.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"capacity": 25},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["capacity"] == 25

    async def test_update_nonexistent_session(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent session returns 404."""
        response = await client.patch(
            "/api/v1/admin/sessions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminSessionDelete:
    """Test deleting a session."""

    async def test_delete_session(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test deleting an existing session succeeds."""
        location = await create_test_location(db_session)
        session = await create_test_session(
            db_session, location=location, name="Delete Me"
        )

        response = await client.delete(
            f"/api/v1/admin/sessions/{session.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK

        get_response = await client.get(
            f"/api/v1/admin/sessions/{session.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert get_response.status_code == HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_session(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test deleting non-existent session returns 404."""
        response = await client.delete(
            "/api/v1/admin/sessions/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_delete_session_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test deleting a session without authentication fails."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        response = await client.delete(
            f"/api/v1/admin/sessions/{session.id}",
        )
        assert response.status_code in [302, 401, 403]


class TestAdminSessionOccurrences:
    """Test session occurrences retrieval."""

    async def test_list_session_occurrences(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving occurrences for a session."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        response = await client.get(
            f"/api/v1/admin/sessions/{session.id}/occurrences",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, (dict, list))

    async def test_list_nonexistent_session_occurrences(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving occurrences for non-existent session returns 404."""
        response = await client.get(
            "/api/v1/admin/sessions/00000000-0000-0000-0000-000000000000/occurrences",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
