"""
Integration tests for admin caregiver management endpoints.

Tests for caregiver CRUD operations with proper authentication and data verification.
"""

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_caregiver

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminCaregiverList:
    """Test admin caregiver listing endpoint."""

    async def test_list_caregivers_empty(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test listing caregivers when none exist."""
        response = await client.get(
            "/api/v1/admin/caregivers/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        # Should have items list (even if empty)
        assert "items" in data or isinstance(data, list)

    async def test_list_caregivers_with_data(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing caregivers returns all created caregivers."""
        # Create multiple caregivers
        caregiver1 = await create_test_caregiver(
            db_session, email="test1@example.com", name="Caregiver 1"
        )
        caregiver2 = await create_test_caregiver(
            db_session, email="test2@example.com", name="Caregiver 2"
        )

        response = await client.get(
            "/api/v1/admin/caregivers/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Extract items - handle both dict with "items" and direct list
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 2

        # Verify caregivers are in list
        emails = [item.get("email") for item in items]
        assert caregiver1.email in emails
        assert caregiver2.email in emails

    async def test_list_caregivers_without_auth(self, client: AsyncClient) -> None:
        """Test listing caregivers without authentication fails."""
        response = await client.get("/api/v1/admin/caregivers/")
        # Should redirect or return 401/403
        assert response.status_code in [302, 401, 403]


class TestAdminCaregiverCreate:
    """Test admin caregiver creation endpoint."""

    async def test_create_caregiver_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a new caregiver with all required fields."""
        response = await client.post(
            "/api/v1/admin/caregivers/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "email": "newcaregiver@example.com",
                "name": "New Caregiver",
                "phone": "555-1234",
                "emailVerified": True,
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newcaregiver@example.com"
        assert data["name"] == "New Caregiver"
        assert "id" in data

    async def test_create_caregiver_without_auth(self, client: AsyncClient) -> None:
        """Test creating a caregiver without authentication fails."""
        response = await client.post(
            "/api/v1/admin/caregivers/",
            json={
                "email": "newcaregiver@example.com",
                "name": "New Caregiver",
            },
        )
        # Should redirect or return 401/403
        assert response.status_code in [302, 401, 403]

    async def test_create_caregiver_minimal(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a caregiver with minimal fields succeeds."""
        response = await client.post(
            "/api/v1/admin/caregivers/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "email": "minimal@example.com",
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "minimal@example.com"


class TestAdminCaregiverGet:
    """Test retrieving a specific caregiver."""

    async def test_get_caregiver(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving a caregiver by ID returns all fields."""
        caregiver = await create_test_caregiver(
            db_session, email="get@example.com", name="Test Caregiver"
        )

        response = await client.get(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["email"] == "get@example.com"
        assert data["name"] == "Test Caregiver"
        assert str(data["id"]) == str(caregiver.id)

    async def test_get_nonexistent_caregiver(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent caregiver returns 404."""
        response = await client.get(
            "/api/v1/admin/caregivers/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminCaregiverUpdate:
    """Test updating a caregiver."""

    async def test_update_caregiver_name(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating caregiver name succeeds."""
        caregiver = await create_test_caregiver(
            db_session, email="update@example.com", name="Original Name"
        )

        response = await client.patch(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated Name"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "update@example.com"  # Should remain unchanged

    async def test_update_caregiver_email(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating caregiver email succeeds."""
        caregiver = await create_test_caregiver(
            db_session, email="old@example.com", name="Test"
        )

        response = await client.patch(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"email": "new@example.com"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["email"] == "new@example.com"

    async def test_update_nonexistent_caregiver(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent caregiver returns 404."""
        response = await client.patch(
            "/api/v1/admin/caregivers/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminCaregiverDelete:
    """Test deleting a caregiver."""

    async def test_delete_caregiver(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test deleting a caregiver succeeds."""
        caregiver = await create_test_caregiver(
            db_session, email="delete@example.com", name="To Delete"
        )

        response = await client.delete(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert get_response.status_code == HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_caregiver(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test deleting non-existent caregiver returns 404."""
        response = await client.delete(
            "/api/v1/admin/caregivers/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminCaregiverStudents:
    """Test listing caregiver's students."""

    async def test_list_caregiver_students(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving students for a caregiver."""
        caregiver = await create_test_caregiver(db_session, email="parent@example.com")

        response = await client.get(
            f"/api/v1/admin/caregivers/{caregiver.id}/students",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        # Should at minimum be a list or dict with items
        assert isinstance(data, (dict, list))

    async def test_list_nonexistent_caregiver_students(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving students for non-existent caregiver returns 404."""
        response = await client.get(
            "/api/v1/admin/caregivers/00000000-0000-0000-0000-000000000000/students",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
