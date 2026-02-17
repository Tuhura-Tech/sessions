"""Tests for reported bugs in admin endpoints.

Bug 1: Attendance shows students on the waitlist
Bug 2: Changing a student from withdrawn to active fails
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.lib.auth import utcnow
from tests.integration.test_fixtures import (
    create_test_block,
    create_test_location,
    create_test_session,
    create_test_student,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


# Note: create_test_student is already in test_fixtures.py


class TestAttendanceWaitlistBug:
    """Tests for bug: Attendance shows students on the waitlist.

    Expected behavior: Attendance roll should only show confirmed students,
    not waitlisted students. Waitlisted students shouldn't be able to attend.
    """

    async def test_attendance_roll_only_shows_confirmed_students(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_session_cookie: str,
    ) -> None:
        """Test that attendance roll excludes waitlisted students."""
        # Create session with capacity 1
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location, capacity=1)
        block = await create_test_block(db_session)

        # Create occurrence
        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=utcnow(),
            ends_at=utcnow() + timedelta(hours=1),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.flush()

        # Create caregiver and two students
        caregiver = m.Caregiver(
            name="Test Caregiver", email="test@example.com", phone="555-1234"
        )
        db_session.add(caregiver)
        await db_session.flush()

        student1 = await create_test_student(
            db_session, caregiver=caregiver, name="Confirmed Student"
        )
        student2 = await create_test_student(
            db_session, caregiver=caregiver, name="Waitlist Student"
        )

        # Create confirmed signup for student1
        signup1 = m.Signup(
            session_id=session.id,
            student_id=student1.id,
            status="confirmed",
        )
        db_session.add(signup1)
        await db_session.flush()

        # Create waitlisted signup for student2
        signup2 = m.Signup(
            session_id=session.id,
            student_id=student2.id,
            status="waitlisted",
        )
        db_session.add(signup2)
        await db_session.commit()

        # Get attendance roll
        response = await client.get(
            f"/api/v1/admin/occurrences/{occurrence.id}/roll",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Parse response
        items = data.get("items", [])

        # Should only include confirmed student (student1)
        assert len(items) == 1, f"Expected 1 item, got {len(items)}: {items}"
        assert items[0]["student_name"] == "Confirmed Student"
        assert items[0]["student_id"] == str(student1.id)

        # Should NOT include waitlisted student
        student_names = [item["student_name"] for item in items]
        assert "Waitlist Student" not in student_names, (
            f"Waitlist student should not be in attendance roll. Found: {student_names}"
        )

    async def test_cannot_mark_attendance_for_waitlisted_student(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_session_cookie: str,
    ) -> None:
        """Test that you cannot mark attendance for waitlisted students."""
        # Create session with capacity 1
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location, capacity=1)
        block = await create_test_block(db_session)

        # Create occurrence
        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=utcnow(),
            ends_at=utcnow() + timedelta(hours=1),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.flush()

        # Create caregiver and student
        caregiver = m.Caregiver(
            name="Test Caregiver", email="test@example.com", phone="555-1234"
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = await create_test_student(
            db_session, caregiver=caregiver, name="Waitlist Student"
        )

        # Create waitlisted signup
        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="waitlisted",
        )
        db_session.add(signup)
        await db_session.commit()

        # Try to mark attendance for waitlisted student
        response = await client.post(
            f"/api/v1/admin/occurrences/{occurrence.id}/attendance",
            cookies={"admin_session": admin_session_cookie},
            json=[
                {
                    "student_id": str(student.id),
                    "status": "present",
                }
            ],
        )

        # Should fail with validation error
        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert "waitlisted" in data.get("detail", "").lower(), (
            f"Expected error about waitlisted status. Got: {data}"
        )


class TestWithdrawnToActiveBug:
    """Tests for bug: Changing a student from withdrawn to active fails.

    Expected behavior: Should be able to change signup status from "withdrawn"
    back to "confirmed" or "pending".
    """

    async def test_change_signup_from_withdrawn_to_confirmed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_session_cookie: str,
    ) -> None:
        """Test changing signup status from withdrawn to confirmed."""
        # Create session and location
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        # Create caregiver and student
        caregiver = m.Caregiver(
            name="Test Caregiver", email="test@example.com", phone="555-1234"
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = await create_test_student(
            db_session, caregiver=caregiver, name="ReactivatedStudent"
        )

        # Create withdrawn signup
        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="withdrawn",
            withdrawn_at=utcnow(),
        )
        db_session.add(signup)
        await db_session.commit()

        # Change status to confirmed
        response = await client.patch(
            f"/api/v1/admin/signups/{signup.id}/status",
            cookies={"admin_session": admin_session_cookie},
            json={
                "status": "confirmed",
                "notify_caregiver": False,
            },
        )

        # Should succeed
        assert response.status_code == HTTP_200_OK, (
            f"Failed to change withdrawn to confirmed: {response.status_code} - "
            f"{response.text}"
        )
        data = response.json()

        # Verify response
        assert data["status"] == "confirmed"
        assert data["withdrawn_at"] is None, (
            f"withdrawn_at should be cleared when changing from withdrawn. "
            f"Got: {data['withdrawn_at']}"
        )

    async def test_change_signup_from_withdrawn_to_pending(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_session_cookie: str,
    ) -> None:
        """Test changing signup status from withdrawn to pending."""
        # Create session and location
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        # Create caregiver and student
        caregiver = m.Caregiver(
            name="Test Caregiver", email="test@example.com", phone="555-1234"
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = await create_test_student(
            db_session, caregiver=caregiver, name="ReactivatedStudent"
        )

        # Create withdrawn signup
        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="withdrawn",
            withdrawn_at=utcnow(),
        )
        db_session.add(signup)
        await db_session.commit()

        # Change status to pending
        response = await client.patch(
            f"/api/v1/admin/signups/{signup.id}/status",
            cookies={"admin_session": admin_session_cookie},
            json={
                "status": "pending",
                "notify_caregiver": False,
            },
        )

        # Should succeed
        assert response.status_code == HTTP_200_OK, (
            f"Failed to change withdrawn to pending: {response.status_code} - "
            f"{response.text}"
        )
        data = response.json()

        # Verify response
        assert data["status"] == "pending"
        assert data["withdrawn_at"] is None, (
            f"withdrawn_at should be cleared when changing from withdrawn. "
            f"Got: {data['withdrawn_at']}"
        )

    async def test_withdrawn_at_clears_on_any_status_change_from_withdrawn(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_session_cookie: str,
    ) -> None:
        """Test that withdrawn_at is cleared regardless of new status."""
        # Try changing withdrawn to each of: pending, confirmed, waitlisted
        for idx, target_status in enumerate(["pending", "confirmed", "waitlisted"]):
            # Create session and location for this iteration
            location = await create_test_location(db_session)
            session = await create_test_session(db_session, location=location)

            # Create caregiver and student with unique email
            caregiver = m.Caregiver(
                name="Test Caregiver",
                email=f"test-{idx}@example.com",
                phone="555-1234",
            )
            db_session.add(caregiver)
            await db_session.flush()

            student = await create_test_student(
                db_session,
                caregiver=caregiver,
                name=f"ReactivatedStudent-{target_status}",
            )

            # Create withdrawn signup
            signup = m.Signup(
                session_id=session.id,
                student_id=student.id,
                status="withdrawn",
                withdrawn_at=utcnow(),
            )
            db_session.add(signup)
            await db_session.commit()

            # Change status
            response = await client.patch(
                f"/api/v1/admin/signups/{signup.id}/status",
                cookies={"admin_session": admin_session_cookie},
                json={
                    "status": target_status,
                    "notify_caregiver": False,
                },
            )

            assert response.status_code == HTTP_200_OK, (
                f"Failed to change withdrawn to {target_status}: "
                f"{response.status_code} - {response.text}"
            )
            data = response.json()

            assert data["status"] == target_status
            assert data["withdrawn_at"] is None, (
                f"withdrawn_at should be None when changing from withdrawn to "
                f"{target_status}, but got: {data['withdrawn_at']}"
            )
