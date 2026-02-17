"""
Integration tests for admin signup creation endpoint.

Tests specifically for manual signup creation by admins, including
proper eager loading of relationships to prevent MissingGreenlet errors.

This addresses the bug where creating signups would trigger:
  sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
due to lazy loading of student/caregiver relationships in Pydantic validators.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from litestar import status_codes
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from tests.integration.test_fixtures import create_test_location, create_test_session

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminSignupCreation:
    """Test admin signup creation endpoint with relationship eager loading.

    These tests verify the fix for MissingGreenlet errors that occurred
    when the Pydantic validator accessed student.caregiver relationships
    without proper eager loading.
    """

    async def test_create_signup_loads_relationships_without_error(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ):
        """Test POST /api/v1/admin/signups creates signup and loads relationships.

        This is the primary test for the MissingGreenlet bug fix.
        It verifies that:
        1. Signup creation succeeds without MissingGreenlet errors
        2. Related student and caregiver data are properly loaded via eager loading
        3. The response includes all relationship-derived fields
        """
        # Create test data
        caregiver = m.Caregiver(
            email="parent@example.com",
            name="Test Parent",
            phone="+64 21 123 4567",
            email_verified=True,
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=date.today() - timedelta(days=365 * 10),
            media_consent=True,
        )
        db_session.add(student)
        await db_session.flush()

        location = await create_test_location(db_session, name="Test Venue")
        session = await create_test_session(
            db_session, location=location, name="Test Session"
        )

        # Create signup via admin API - this would previously cause MissingGreenlet error
        response = await client.post(
            "/api/v1/admin/signups/",
            json={
                "studentId": str(student.id),
                "sessionId": str(session.id),
                "status": "waitlisted",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        # Should succeed without errors
        assert response.status_code == status_codes.HTTP_201_CREATED

        data = response.json()

        # Verify core signup data (handle both camelCase and snake_case)
        student_id = data.get("studentId") or data.get("student_id")
        session_id = data.get("sessionId") or data.get("session_id")
        assert student_id == str(student.id)
        assert session_id == str(session.id)
        assert data["status"] == "waitlisted"

        # Verify relationship-derived fields are populated (proving eager loading works)
        # These fields come from the student relationship
        student_name = data.get("studentName") or data.get("student_name")
        date_of_birth = data.get("dateOfBirth") or data.get("date_of_birth")
        media_consent = data.get("mediaConsent") or data.get("media_consent")
        assert student_name == "Test Student"
        assert date_of_birth is not None
        assert media_consent is True

        # These fields come from the student.caregiver relationship
        # (the problematic nested relationship that caused the bug)
        guardian_name = data.get("guardianName") or data.get("guardian_name")
        assert guardian_name == "Test Parent"
        assert data["email"] == "parent@example.com"
        assert data["phone"] == "+64 21 123 4567"

    async def test_create_multiple_signups_no_lazy_load_errors(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ):
        """Test creating multiple signups in sequence doesn't trigger lazy load errors.

        Verifies the fix works consistently across multiple requests.
        """
        # Create test data
        caregiver = m.Caregiver(
            email="parent@example.com",
            name="Test Parent",
            phone="+64 21 123 4567",
            email_verified=True,
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create multiple students
        students = []
        for i in range(3):
            student = m.Student(
                caregiver_id=caregiver.id,
                name=f"Student {i + 1}",
                date_of_birth=date.today() - timedelta(days=365 * (8 + i)),
                media_consent=True,
            )
            db_session.add(student)
            students.append(student)
        await db_session.flush()

        # Create multiple sessions
        location = await create_test_location(db_session)
        sessions = []
        for i in range(2):
            sess = await create_test_session(
                db_session, location=location, name=f"Session {i + 1}"
            )
            sessions.append(sess)

        # Create signups for all combinations
        for student in students:
            for sess in sessions:
                response = await client.post(
                    "/api/v1/admin/signups/",
                    json={
                        "studentId": str(student.id),
                        "sessionId": str(sess.id),
                        "status": "pending",
                    },
                    cookies={"admin_session": admin_session_cookie},
                )

                # Each should succeed without lazy load errors
                assert response.status_code == status_codes.HTTP_201_CREATED

                data = response.json()
                # Verify relationships loaded properly (handle both cases)
                student_name = data.get("studentName") or data.get("student_name")
                guardian_name = data.get("guardianName") or data.get("guardian_name")
                assert student_name in [f"Student {i + 1}" for i in range(3)]
                assert guardian_name == "Test Parent"
                assert data["email"] == "parent@example.com"

    async def test_create_signup_with_optional_fields(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ):
        """Test creating signup with optional fields populates all data correctly."""
        caregiver = m.Caregiver(
            email="parent@example.com",
            name="Test Parent",
            phone="+64 21 987 6543",
            email_verified=True,
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=date.today() - timedelta(days=365 * 9),
            media_consent=False,
        )
        db_session.add(student)
        await db_session.flush()

        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        response = await client.post(
            "/api/v1/admin/signups/",
            json={
                "studentId": str(student.id),
                "sessionId": str(session.id),
                "status": "confirmed",
                "pickupDropoff": "Parent will drop off and pick up",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == status_codes.HTTP_201_CREATED

        data = response.json()
        assert data["status"] == "confirmed"
        pickup_dropoff = data.get("pickupDropoff") or data.get("pickup_dropoff")
        assert pickup_dropoff == "Parent will drop off and pick up"

        # Relationships should still be loaded correctly (handle both cases)
        student_name = data.get("studentName") or data.get("student_name")
        guardian_name = data.get("guardianName") or data.get("guardian_name")
        media_consent = data.get("mediaConsent") or data.get("media_consent")
        assert student_name == "Test Student"
        assert guardian_name == "Test Parent"
        assert media_consent is False

    async def test_create_signup_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that signup creation requires admin authentication."""
        caregiver = m.Caregiver(
            email="parent@example.com",
            name="Test Parent",
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        # Attempt without authentication
        response = await client.post(
            "/api/v1/admin/signups/",
            json={
                "studentId": str(student.id),
                "sessionId": str(session.id),
                "status": "pending",
            },
        )

        # Should require authentication
        assert response.status_code == status_codes.HTTP_401_UNAUTHORIZED

    async def test_create_signup_invalid_student_fails(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ):
        """Test creating signup with non-existent student fails gracefully."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        response = await client.post(
            "/api/v1/admin/signups/",
            json={
                "studentId": "00000000-0000-0000-0000-000000000000",
                "sessionId": str(session.id),
                "status": "pending",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        # Should fail with foreign key constraint error
        assert response.status_code in (
            status_codes.HTTP_400_BAD_REQUEST,
            status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    async def test_create_signup_enforces_unique_constraint(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ):
        """Test that duplicate signups for same student+session are prevented."""
        caregiver = m.Caregiver(
            email="parent@example.com",
            name="Test Parent",
        )
        db_session.add(caregiver)
        await db_session.flush()

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)

        signup_data = {
            "studentId": str(student.id),
            "sessionId": str(session.id),
            "status": "pending",
        }

        # First creation should succeed
        response1 = await client.post(
            "/api/v1/admin/signups/",
            json=signup_data,
            cookies={"admin_session": admin_session_cookie},
        )
        assert response1.status_code == status_codes.HTTP_201_CREATED

        # Second creation should fail due to unique constraint
        response2 = await client.post(
            "/api/v1/admin/signups/",
            json=signup_data,
            cookies={"admin_session": admin_session_cookie},
        )
        assert response2.status_code in (
            status_codes.HTTP_400_BAD_REQUEST,
            status_codes.HTTP_409_CONFLICT,
            status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
        )
