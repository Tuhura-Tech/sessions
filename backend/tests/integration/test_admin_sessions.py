"""
Integration tests for admin session management endpoints.

Tests for session CRUD operations with proper authentication and data verification.
"""

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
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
                "whatToBring": "Water bottle",
                "prerequisites": "None",
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Session"
        assert data["capacity"] == 15
        assert data["year"] == 2025
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
            json={"name": "Updated Name"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

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
