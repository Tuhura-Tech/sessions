"""Tests for admin student management endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

from tests.factories import CaregiverFactory, StudentFactory

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminStudentManagement:
    """Test admin student management endpoints."""

    async def test_list_students_requires_auth(self, client: AsyncClient) -> None:
        """Test that student list requires authentication."""
        response = await client.get("/api/v1/admin/students/")
        assert response.status_code in [401, 403]

    async def test_list_students_with_auth(
        self, admin_session_cookie: str, client: AsyncClient, db_session
    ) -> None:
        """Test listing students with admin auth."""
        # Create test students
        caregiver = await db_session.merge(CaregiverFactory.build())
        await db_session.commit()

        for i in range(2):
            await db_session.merge(
                StudentFactory.build(
                    caregiver_id=caregiver.id,
                    name=f"Test Student {i}",
                )
            )
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/students/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data is not None

    async def test_get_student_requires_auth(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test that getting student requires authentication."""
        caregiver = await db_session.merge(CaregiverFactory.build())
        student = await db_session.merge(
            StudentFactory.build(caregiver_id=caregiver.id)
        )
        await db_session.commit()

        response = await client.get(f"/api/v1/admin/students/{student.id}")
        assert response.status_code in [401, 403]

    async def test_get_student_with_auth(
        self, admin_session_cookie: str, client: AsyncClient, db_session
    ) -> None:
        """Test getting a specific student with admin auth."""
        caregiver = await db_session.merge(CaregiverFactory.build())
        student = await db_session.merge(
            StudentFactory.build(
                caregiver_id=caregiver.id,
                name="Test Student Get",
            )
        )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "id" in data or "name" in data

    async def test_get_nonexistent_student(
        self, admin_session_cookie: str, client: AsyncClient
    ) -> None:
        """Test getting non-existent student returns 404."""
        response = await client.get(
            "/api/v1/admin/students/nonexistent-id",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
