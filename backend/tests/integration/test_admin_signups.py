"""
Integration tests for admin signup management endpoints.

Tests signup get by ID, create, and update operations.
Note: No list endpoint exists for signups - only individual operations.
"""

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.db import models as m
from tests.integration.test_fixtures import (
    create_test_caregiver,
    create_test_location,
    create_test_session,
    create_test_student,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminSignupGet:
    """Test retrieving signup by ID."""

    async def test_get_signup_by_id(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving specific signup returns complete data."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        signup = m.Signup(
            student_id=student.id,
            session_id=session.id,
            status="pending",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/signups/{signup.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "pending"
        assert data.get("studentId") or data.get("student_id") == str(student.id)
        assert data.get("sessionId") or data.get("session_id") == str(session.id)

    async def test_get_nonexistent_signup(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent signup returns 404."""
        response = await client.get(
            f"/api/v1/admin/signups/{uuid4()}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_signup_without_auth(self, client: AsyncClient) -> None:
        """Test retrieving signup without authentication fails."""
        response = await client.get(f"/api/v1/admin/signups/{uuid4()}")
        assert response.status_code in [302, 401, 403]


class TestAdminSignupCreate:
    """Test signup creation."""

    async def test_create_signup_success(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating a new signup succeeds."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        signup_data = {
            "studentId": str(student.id),
            "sessionId": str(session.id),
            "status": "confirmed",
        }

        response = await client.post(
            "/api/v1/admin/signups/",
            json=signup_data,
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "confirmed"
        assert data.get("studentId") or data.get("student_id") == str(student.id)
        assert data.get("sessionId") or data.get("session_id") == str(session.id)

    async def test_create_signup_without_auth(self, client: AsyncClient) -> None:
        """Test creating signup without authentication fails."""
        response = await client.post(
            "/api/v1/admin/signups/",
            json={
                "studentId": str(uuid4()),
                "sessionId": str(uuid4()),
                "status": "confirmed",
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminSignupUpdate:
    """Test signup update operations."""

    async def test_update_signup_status(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating signup status."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        signup = m.Signup(
            student_id=student.id,
            session_id=session.id,
            status="pending",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/signups/{signup.id}",
            json={"status": "confirmed"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "confirmed"

        # Verify database was updated
        await db_session.refresh(signup)
        assert signup.status == "confirmed"

    async def test_update_signup_pickup_dropoff(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating signup pickup/dropoff information."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        signup = m.Signup(
            student_id=student.id,
            session_id=session.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/signups/{signup.id}",
            json={"pickupDropoff": "Pickup at main entrance"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "pickupDropoff" in data or "pickup_dropoff" in data

        # Verify database was updated
        await db_session.refresh(signup)
        assert signup.pickup_dropoff == "Pickup at main entrance"

    async def test_update_signup_to_withdrawn_sets_timestamp(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test that updating to withdrawn status sets withdrawn_at timestamp."""
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        signup = m.Signup(
            student_id=student.id,
            session_id=session.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        assert signup.withdrawn_at is None

        response = await client.patch(
            f"/api/v1/admin/signups/{signup.id}",
            json={"status": "withdrawn"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["status"] == "withdrawn"

        # Verify withdrawn_at was set
        await db_session.refresh(signup)
        assert signup.withdrawn_at is not None
        assert signup.status == "withdrawn"

    async def test_update_nonexistent_signup(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent signup returns 404."""
        response = await client.patch(
            f"/api/v1/admin/signups/{uuid4()}",
            json={"status": "confirmed"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_update_signup_without_auth(self, client: AsyncClient) -> None:
        """Test updating signup without authentication fails."""
        response = await client.patch(
            f"/api/v1/admin/signups/{uuid4()}",
            json={"status": "confirmed"},
        )
        assert response.status_code in [302, 401, 403]
