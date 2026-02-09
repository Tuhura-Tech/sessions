"""
Integration tests for admin delete operations with cascade behavior.

Tests ensure that deleting caregivers and students properly cascades to related entities.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.db.models.attendance import AttendanceStatus


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminDeleteCaregiverWithCascade:
    """Test admin caregiver deletion with cascading deletes."""

    async def test_delete_caregiver_without_students(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a caregiver with no students succeeds."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="lone.caregiver@test.com", name="Lone Caregiver", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.commit()

        # Delete caregiver
        response = await test_client.delete(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify caregiver is deleted
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_caregiver_with_students(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a caregiver cascades to their students."""
        # Create caregiver with students
        caregiver = m.Caregiver(
            email="parent@test.com", name="Parent User", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.flush()

        student1 = m.Student(
            caregiver_id=caregiver.id,
            name="Student One",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        student2 = m.Student(
            caregiver_id=caregiver.id,
            name="Student Two",
            date_of_birth=date.today() - timedelta(days=365 * 8),
        )
        db_session.add_all([student1, student2])
        await db_session.commit()

        student1_id = student1.id
        student2_id = student2.id

        # Delete caregiver
        response = await test_client.delete(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify caregiver is deleted
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify students are also deleted (cascade)
        result = await db_session.execute(
            select(m.Student).where(m.Student.id.in_([student1_id, student2_id]))
        )
        assert result.scalars().all() == []

    async def test_delete_caregiver_with_students_and_signups(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a caregiver cascades to students and their signups."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="parent.signup@test.com",
            name="Parent with Signups",
            email_verified=True,
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create student
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student with Signup",
            date_of_birth=date.today() - timedelta(days=365 * 9),
        )
        db_session.add(student)
        await db_session.flush()

        # Create session
        location = m.Location(
            name="Test Location",
            address="123 Test St",
            region="Test Region",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        session = m.Session(
            name="Test Session",
            year=2026,
            age_lower=8,
            age_upper=12,
            day_of_week=1,  # Monday
            start_time=time(9, 0),
            end_time=time(15, 0),
            capacity=20,
            location_id=location.id,
        )
        db_session.add(session)
        await db_session.flush()

        # Create signup
        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        signup_id = signup.id
        student_id = student.id

        # Delete caregiver
        response = await test_client.delete(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify caregiver is deleted
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify student is deleted
        result = await db_session.execute(
            select(m.Student).where(m.Student.id == student_id)
        )
        assert result.scalar_one_or_none() is None

        # Verify signup is also deleted (cascade from student)
        result = await db_session.execute(
            select(m.Signup).where(m.Signup.id == signup_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_caregiver_cascades_to_magic_links_and_sessions(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a caregiver cascades to their magic links and sessions."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="test.auth@test.com", name="Test Auth User", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create magic link
        magic_link = m.CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash="test_hash_12345",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(magic_link)

        # Create session
        session = m.CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash="session_hash_67890",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            user_agent="Test Browser",
            ip_address="127.0.0.1",
        )
        db_session.add(session)
        await db_session.commit()

        magic_link_id = magic_link.id
        session_id = session.id

        # Delete caregiver
        response = await test_client.delete(
            f"/api/v1/admin/caregivers/{caregiver.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify caregiver is deleted
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify magic link is deleted (CASCADE)
        result = await db_session.execute(
            select(m.CaregiverMagicLink).where(m.CaregiverMagicLink.id == magic_link_id)
        )
        assert result.scalar_one_or_none() is None

        # Verify session is deleted (CASCADE)
        result = await db_session.execute(
            select(m.CaregiverSession).where(m.CaregiverSession.id == session_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_caregiver(
        self, test_client, admin_session_cookie: str
    ):
        """Test deleting a nonexistent caregiver returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(
            f"/api/v1/admin/caregivers/{fake_id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminDeleteStudentWithCascade:
    """Test admin student deletion with cascading deletes."""

    async def test_delete_student_without_signups(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a student with no signups succeeds."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="parent.nostudents@test.com", name="Parent", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create student
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Lone Student",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.commit()

        # Delete student
        response = await test_client.delete(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify student is deleted
        result = await db_session.execute(
            select(m.Student).where(m.Student.id == student.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify caregiver still exists
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is not None

    async def test_delete_student_with_signups(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a student cascades to their signups."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="parent.withsignups@test.com", name="Parent", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create student
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student with Signups",
            date_of_birth=date.today() - timedelta(days=365 * 9),
        )
        db_session.add(student)
        await db_session.flush()

        # Create location and sessions
        location = m.Location(
            name="Test Location",
            address="456 Test Ave",
            region="Test Region",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        session1 = m.Session(
            name="Session One",
            year=2026,
            age_lower=8,
            age_upper=12,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(15, 0),
            capacity=20,
            location_id=location.id,
        )
        session2 = m.Session(
            name="Session Two",
            year=2026,
            age_lower=8,
            age_upper=12,
            day_of_week=3,
            start_time=time(10, 0),
            end_time=time(14, 0),
            capacity=15,
            location_id=location.id,
        )
        db_session.add_all([session1, session2])
        await db_session.flush()

        # Create multiple signups
        signup1 = m.Signup(
            session_id=session1.id,
            student_id=student.id,
            status="confirmed",
        )
        signup2 = m.Signup(
            session_id=session2.id,
            student_id=student.id,
            status="pending",
        )
        db_session.add_all([signup1, signup2])
        await db_session.commit()

        signup1_id = signup1.id
        signup2_id = signup2.id

        # Delete student
        response = await test_client.delete(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify student is deleted
        result = await db_session.execute(
            select(m.Student).where(m.Student.id == student.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify signups are deleted (cascade)
        result = await db_session.execute(
            select(m.Signup).where(m.Signup.id.in_([signup1_id, signup2_id]))
        )
        assert result.scalars().all() == []

        # Verify caregiver still exists
        result = await db_session.execute(
            select(m.Caregiver).where(m.Caregiver.id == caregiver.id)
        )
        assert result.scalar_one_or_none() is not None

        # Verify sessions still exist
        result = await db_session.execute(
            select(m.Session).where(m.Session.id.in_([session1.id, session2.id]))
        )
        assert len(result.scalars().all()) == 2

    async def test_delete_student_with_attendance_records(
        self, test_client, db_session: AsyncSession, admin_session_cookie: str
    ):
        """Test deleting a student cascades to their attendance records."""
        # Create caregiver
        caregiver = m.Caregiver(
            email="parent.attendance@test.com", name="Parent", email_verified=True
        )
        db_session.add(caregiver)
        await db_session.flush()

        # Create student
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student with Attendance",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        # Create block, location, session, and occurrence
        block = m.Block(
            name="Term 1",
            year=2026,
            block_type="term_1",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
        )
        db_session.add(block)
        await db_session.flush()

        location = m.Location(
            name="Test Location",
            address="789 Test Rd",
            region="Test Region",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        session = m.Session(
            name="Attendance Session",
            year=2026,
            age_lower=8,
            age_upper=12,
            day_of_week=2,
            start_time=time(9, 0),
            end_time=time(15, 0),
            capacity=20,
            location_id=location.id,
        )
        db_session.add(session)
        await db_session.flush()

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 2, 10, 15, 0, tzinfo=timezone.utc),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.flush()

        # Create attendance record
        attendance = m.AttendanceRecord(
            occurrence_id=occurrence.id,
            student_id=student.id,
            status=AttendanceStatus.PRESENT,
        )
        db_session.add(attendance)
        await db_session.commit()

        attendance_id = attendance.id

        # Delete student
        response = await test_client.delete(
            f"/api/v1/admin/students/{student.id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK

        # Verify student is deleted
        result = await db_session.execute(
            select(m.Student).where(m.Student.id == student.id)
        )
        assert result.scalar_one_or_none() is None

        # Verify attendance record is deleted (cascade)
        result = await db_session.execute(
            select(m.AttendanceRecord).where(m.AttendanceRecord.id == attendance_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_student(
        self, test_client, admin_session_cookie: str
    ):
        """Test deleting a nonexistent student returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(
            f"/api/v1/admin/students/{fake_id}",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
