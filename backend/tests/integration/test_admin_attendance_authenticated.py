"""Tests for admin attendance endpoints with authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from tests.integration.test_fixtures import (
    create_test_block,
    create_test_caregiver,
    create_test_session,
    create_test_student,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminAttendanceRollGet:
    """Tests for GET /api/v1/admin/occurrences/:occurrence_id/roll endpoint."""

    async def test_get_roll_success(
        self,
        client: AsyncClient,
        admin_session_cookie: str,
        db_session: AsyncSession,
    ) -> None:
        """Test successfully getting attendance roll for valid occurrence."""
        session = await create_test_session(db_session)
        block = await create_test_block(db_session)
        starts_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/occurrences/{occurrence.id}/roll",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["occurrence_id"] == str(occurrence.id)
        assert "session_id" in data
        assert "starts_at" in data
        assert "ends_at" in data
        assert "cancelled" in data
        assert isinstance(data["items"], list)

    async def test_get_roll_nonexistent_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test that getting roll for non-existent occurrence returns 404."""
        fake_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        response = await client.get(
            f"/api/v1/admin/occurrences/{fake_id}/roll",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_get_roll_requires_authentication(self, client: AsyncClient) -> None:
        """Test that attendance roll endpoint requires authentication."""
        fake_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        response = await client.get(
            f"/api/v1/admin/occurrences/{fake_id}/roll",
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestAdminAttendanceSavePost:
    """Tests for POST /api/v1/admin/occurrences/:occurrence_id/attendance endpoint."""

    async def test_save_attendance_success(
        self,
        client: AsyncClient,
        admin_session_cookie: str,
        db_session: AsyncSession,
    ) -> None:
        """Test successfully saving attendance for valid occurrence."""
        # Create session with test data
        session = await create_test_session(db_session)
        block = await create_test_block(db_session)
        caregiver = await create_test_caregiver(db_session)
        student = await create_test_student(db_session, caregiver=caregiver)
        starts_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)

        # Create occurrence linked to session
        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db_session.add(occurrence)
        await db_session.commit()

        # Create confirmed signup to allow attendance marking
        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/occurrences/{occurrence.id}/attendance",
            cookies={"admin_session": admin_session_cookie},
            json=[
                {
                    "student_id": str(student.id),
                    "status": "present",
                    "reason": None,
                }
            ],
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "student_id" in data[0]
        assert "status" in data[0]

    async def test_save_attendance_nonexistent_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test saving attendance for non-existent occurrence returns 404."""
        fake_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        response = await client.post(
            f"/api/v1/admin/occurrences/{fake_id}/attendance",
            cookies={"admin_session": admin_session_cookie},
            json=[
                {
                    "student_id": str(UUID("550e8400-e29b-41d4-a716-446655440001")),
                    "status": "present",
                }
            ],
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_save_attendance_empty_array_fails(
        self,
        client: AsyncClient,
        admin_session_cookie: str,
        db_session: AsyncSession,
    ) -> None:
        """Test that save attendance rejects empty arrays."""
        session = await create_test_session(db_session)
        block = await create_test_block(db_session)
        starts_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/occurrences/{occurrence.id}/attendance",
            cookies={"admin_session": admin_session_cookie},
            json=[],
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_save_attendance_invalid_json_fails(
        self,
        client: AsyncClient,
        admin_session_cookie: str,
        db_session: AsyncSession,
    ) -> None:
        """Test that save attendance fails with invalid payload structure."""
        session = await create_test_session(db_session)
        block = await create_test_block(db_session)
        starts_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/occurrences/{occurrence.id}/attendance",
            cookies={"admin_session": admin_session_cookie},
            json={
                "student_id": str(UUID("550e8400-e29b-41d4-a716-446655440001")),
                "status": "present",
            },
        )

        # Should fail because it expects an array, not an object
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_save_attendance_requires_authentication(
        self, client: AsyncClient
    ) -> None:
        """Test that save attendance endpoint requires authentication."""
        fake_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        response = await client.post(
            f"/api/v1/admin/occurrences/{fake_id}/attendance",
            json=[],
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED
