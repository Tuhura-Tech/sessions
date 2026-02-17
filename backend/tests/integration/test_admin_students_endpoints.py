"""Tests for admin student management endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_student, create_test_caregiver

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminStudentList:
    """Test admin student listing endpoint."""

    async def test_list_students_empty(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test listing students when none exist."""
        response = await client.get(
            "/api/v1/admin/students/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data or isinstance(data, list)

    async def test_list_students_with_data(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing students returns all created students."""
        caregiver = await create_test_caregiver(db_session, email="parent1@example.com")
        student1 = await create_test_student(
            db_session, caregiver=caregiver, name="Student 1"
        )
        student2 = await create_test_student(
            db_session, caregiver=caregiver, name="Student 2"
        )

        response = await client.get(
            "/api/v1/admin/students/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 2

        names = [item.get("name") for item in items]
        assert student1.name in names
        assert student2.name in names

    async def test_list_students_without_auth(self, client: AsyncClient) -> None:
        """Test listing students without authentication fails."""
        response = await client.get("/api/v1/admin/students/")
        assert response.status_code in [302, 401, 403]


class TestAdminStudentCreate:
    """Test admin student creation endpoint."""

    async def test_create_student_success(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating a new student with all required fields."""
        caregiver = await create_test_caregiver(db_session)

        response = await client.post(
            "/api/v1/admin/students/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "New Student",
                "caregiverId": str(caregiver.id),
                "dateOfBirth": "2015-05-10",
                "mediaConsent": True,
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Student"
        assert "id" in data

    async def test_create_student_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating a student without authentication fails."""
        caregiver = await create_test_caregiver(db_session)
        response = await client.post(
            "/api/v1/admin/students/",
            json={
                "name": "New Student",
                "caregiverId": str(caregiver.id),
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminStudentGet:
    """Test retrieving a specific student."""

    async def test_get_student(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving a student by ID returns all fields."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(
            db_session, caregiver=caregiver, name="Get Test Student"
        )

        response = await client.get(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Get Test Student"
        assert str(data["id"]) == str(student.id)
        # Check for caregiver relationship
        assert "caregiver" in data or "caregiverId" in data or "caregiver_id" in data

    async def test_get_nonexistent_student(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent student returns 404."""
        response = await client.get(
            "/api/v1/admin/students/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_student_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a student without authentication fails."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)

        response = await client.get(f"/api/v1/admin/students/{student.id}")
        assert response.status_code in [401, 403]


class TestAdminStudentUpdate:
    """Test updating a student."""

    async def test_update_student_name(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating student name succeeds."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(
            db_session, caregiver=caregiver, name="Original Name"
        )

        response = await client.patch(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated Name"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_update_nonexistent_student(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent student returns 404."""
        response = await client.patch(
            "/api/v1/admin/students/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminStudentDelete:
    """Test deleting a student."""

    async def test_delete_student(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test deleting a student succeeds."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(
            db_session, caregiver=caregiver, name="To Delete"
        )

        response = await client.delete(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert get_response.status_code == HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_student(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test deleting non-existent student returns 404."""
        response = await client.delete(
            "/api/v1/admin/students/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminStudentSignups:
    """Test retrieving student signups."""

    async def test_list_student_signups(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving signups for a student."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)

        response = await client.get(
            f"/api/v1/admin/students/{student.id}/signups",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, (dict, list))

    async def test_list_nonexistent_student_signups(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving signups for non-existent student returns 404."""
        response = await client.get(
            "/api/v1/admin/students/00000000-0000-0000-0000-000000000000/signups",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
