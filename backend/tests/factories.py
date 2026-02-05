"""Test data factories for session management system using Polyfactory."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

from polyfactory import Ignore, Use
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.db import models as m


class LocationFactory(SQLAlchemyFactory[m.Location]):
    """Factory for Location model."""

    __model__ = m.Location
    __set_relationships__ = True

    id = Use(uuid4)
    name = Use(lambda: f"Test Location {uuid4().hex[:6]}")
    address = Use(lambda: f"{uuid4().hex[:8]} Test Street")
    region = Use(lambda: f"Region {uuid4().hex[:4]}")
    lat = Use(lambda: -41.2865 + (float(uuid4().int) % 100) / 1000)
    lng = Use(lambda: 174.7762 + (float(uuid4().int) % 100) / 1000)
    contact_name = Use(lambda: f"Contact {uuid4().hex[:6]}")
    contact_email = Use(lambda: f"contact{uuid4().hex[:8]}@example.com")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    sessions = Ignore()


class BlockFactory(SQLAlchemyFactory[m.Block]):
    """Factory for Block model."""

    __model__ = m.Block
    __set_relationships__ = True

    id = Use(uuid4)
    year = Use(lambda: 2026)
    name = Use(lambda: f"Term {uuid4().hex[:2]}")
    start_date = Use(lambda: date.today())
    end_date = Use(lambda: date.today() + timedelta(days=90))
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    block_links = Ignore()
    occurrences = Ignore()


class CaregiverFactory(SQLAlchemyFactory[m.Caregiver]):
    """Factory for Caregiver model."""

    __model__ = m.Caregiver
    __set_relationships__ = True

    id = Use(uuid4)
    email = Use(lambda: f"caregiver{uuid4().hex[:8]}@example.com")
    name = Use(lambda: f"Caregiver {uuid4().hex[:6]}")
    phone = Use(lambda: f"+64 {uuid4().int % 1000000000:09d}")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    students = Ignore()


class StudentFactory(SQLAlchemyFactory[m.Student]):
    """Factory for Student model."""

    __model__ = m.Student
    __set_relationships__ = True

    id = Use(uuid4)
    caregiver_id = Use(uuid4)
    name = Use(lambda: f"Student {uuid4().hex[:6]}")
    date_of_birth = Use(lambda: date.today() - timedelta(days=365 * 10))
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    caregiver = Ignore()
    signups = Ignore()
    attendence_records = Ignore()


class SessionFactory(SQLAlchemyFactory[m.Session]):
    """Factory for Session model."""

    __model__ = m.Session
    __set_relationships__ = True

    id = Use(uuid4)
    location_id = Use(uuid4)
    name = Use(lambda: f"Session {uuid4().hex[:6]}")
    year = Use(lambda: 2026)
    age_lower = Use(lambda: 5)
    age_upper = Use(lambda: 12)
    session_type = Use(lambda: "special")
    day_of_week = Use(lambda: 0)
    start_time = Use(lambda: time(9, 0))
    end_time = Use(lambda: time(17, 0))
    capacity = Use(lambda: 20)
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    location = Ignore()
    occurrences = Ignore()
    signups = Ignore()
    block_links = Ignore()
    session_staff_assignments = Ignore()


class OccurrenceFactory(SQLAlchemyFactory[m.Occurrence]):
    """Factory for Occurrence model."""

    __model__ = m.Occurrence
    __set_relationships__ = True

    id = Use(uuid4)
    session_id = Use(uuid4)
    block_id = Use(uuid4)
    starts_at = Use(lambda: datetime.now(UTC) + timedelta(days=7))
    ends_at = Use(lambda: datetime.now(UTC) + timedelta(days=7, hours=8))
    cancelled = False
    cancellation_reason = None
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    session = Ignore()
    block = Ignore()


class SignupFactory(SQLAlchemyFactory[m.Signup]):
    """Factory for Signup model."""

    __model__ = m.Signup
    __set_relationships__ = True

    id = Use(uuid4)
    student_id = Use(uuid4)
    session_id = Use(uuid4)
    status = Use(lambda: "confirmed")
    withdrawn_at = None
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    student = Ignore()
    session = Ignore()


class AttendanceRecordFactory(SQLAlchemyFactory[m.AttendanceRecord]):
    """Factory for AttendanceRecord model."""

    __model__ = m.AttendanceRecord
    __set_relationships__ = True

    id = Use(uuid4)
    occurrence_id = Use(uuid4)
    student_id = Use(uuid4)
    status = Use(lambda: "present")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    occurrence = Ignore()
    student = Ignore()


class ExclusionDateFactory(SQLAlchemyFactory[m.ExclusionDate]):
    """Factory for ExclusionDate model."""

    __model__ = m.ExclusionDate
    __set_relationships__ = True

    id = Use(uuid4)
    year = Use(lambda: 2026)
    date = Use(lambda: date.today() + timedelta(days=7))
    reason = Use(lambda: f"Exclusion reason {uuid4().hex[:4]}")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))


class StaffFactory(SQLAlchemyFactory[m.Staff]):
    """Factory for Staff model."""

    __model__ = m.Staff
    __set_relationships__ = True

    id = Use(uuid4)
    name = Use(lambda: f"Staff {uuid4().hex[:6]}")
    email = Use(lambda: f"staff{uuid4().hex[:8]}@example.com")
    sso_id = Use(lambda: f"sso_{uuid4().hex[:12]}")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    session_assignments = Ignore()


class SessionStaffFactory(SQLAlchemyFactory[m.SessionStaff]):
    """Factory for SessionStaff model."""

    __model__ = m.SessionStaff
    __set_relationships__ = True

    id = Use(uuid4)
    session_id = Use(uuid4)
    staff_id = Use(uuid4)
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    session = Ignore()
    staff = Ignore()


class BlockLinkFactory(SQLAlchemyFactory[m.BlockLink]):
    """Factory for BlockLink model."""

    __model__ = m.BlockLink
    __set_relationships__ = True

    id = Use(uuid4)
    block_id = Use(uuid4)
    session_id = Use(uuid4)
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))

    # Ignore relationships
    block = Ignore()
    session = Ignore()


class CaregiverMagicLinkFactory(SQLAlchemyFactory[m.CaregiverMagicLink]):
    """Factory for CaregiverMagicLink model."""

    __model__ = m.CaregiverMagicLink
    __set_relationships__ = True

    id = Use(uuid4)
    caregiver_id = Use(uuid4)
    token_hash = Use(lambda: f"hash_{uuid4().hex}")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))
    expires_at = Use(lambda: datetime.now(UTC) + timedelta(hours=24))

    # Ignore relationships
    caregiver = Ignore()


class CaregiverSessionFactory(SQLAlchemyFactory[m.CaregiverSession]):
    """Factory for CaregiverSession model."""

    __model__ = m.CaregiverSession
    __set_relationships__ = True

    id = Use(uuid4)
    caregiver_id = Use(uuid4)
    token_hash = Use(lambda: f"token_{uuid4().hex}")
    created_at = Use(lambda: datetime.now(UTC))
    updated_at = Use(lambda: datetime.now(UTC))
    expires_at = Use(lambda: datetime.now(UTC) + timedelta(days=30))

    # Ignore relationships
    caregiver = Ignore()


# ============================================================================
# Batch creation helpers
# ============================================================================


async def create_complete_block(
    session,
    year: int = 2026,
    block_name: str = "Term 1",
    location_count: int = 1,
    session_count: int = 2,
    occurrence_count: int = 4,
) -> tuple[m.Block, list[m.Session], list[m.Occurrence]]:
    """Create a complete block hierarchy with sessions and occurrences.

    Args:
        session: Database session
        year: Year for the block
        block_name: Name of the block
        location_count: Number of locations to create
        session_count: Number of sessions per location
        occurrence_count: Number of occurrences per session

    Returns:
        Tuple of (block, sessions, occurrences)
    """
    # Create block
    block = BlockFactory.build(year=year, name=block_name)
    session.add(block)
    await session.flush()

    # Create locations and sessions
    sessions = []
    occurrences = []

    for _ in range(location_count):
        location = LocationFactory.build()
        session.add(location)
        await session.flush()

        for _ in range(session_count):
            s = SessionFactory.build(location_id=location.id, year=year)
            session.add(s)
            await session.flush()
            sessions.append(s)

            # Create block link
            link = BlockLinkFactory.build(block_id=block.id, session_id=s.id)
            session.add(link)

            # Create occurrences
            base_date = datetime.now(UTC) + timedelta(days=7)
            for i in range(occurrence_count):
                occ = OccurrenceFactory.build(
                    session_id=s.id,
                    block_id=block.id,
                    starts_at=base_date + timedelta(days=i * 7),
                    ends_at=base_date + timedelta(days=i * 7, hours=8),
                )
                session.add(occ)
                occurrences.append(occ)

    await session.flush()
    return block, sessions, occurrences


async def create_caregiver_with_students(
    session,
    caregiver_email: str = "caregiver@example.com",
    student_count: int = 2,
) -> tuple[m.Caregiver, list[m.Student]]:
    """Create a caregiver with students.

    Args:
        session: Database session
        caregiver_email: Email for the caregiver
        student_count: Number of students to create

    Returns:
        Tuple of (caregiver, students)
    """
    caregiver = CaregiverFactory.build(email=caregiver_email)
    session.add(caregiver)
    await session.flush()

    students = []
    for _ in range(student_count):
        student = StudentFactory.build(caregiver_id=caregiver.id)
        session.add(student)
        students.append(student)

    await session.flush()
    return caregiver, students


async def create_signups(
    session,
    students: list[m.Student],
    sessions: list[m.Session],
    status: str = "confirmed",
    count: int | None = None,
) -> list[m.Signup]:
    """Create signups for students in sessions.

    Args:
        session: Database session
        students: List of students
        sessions: List of sessions
        status: Signup status (confirmed, waitlisted, pending)
        count: Number of signups to create (defaults to len(students) * len(sessions))

    Returns:
        List of created signups
    """
    signups = []
    count = count or len(students) * len(sessions)

    for i in range(count):
        student = students[i % len(students)]
        sess = sessions[i % len(sessions)]

        signup = SignupFactory.build(
            student_id=student.id,
            session_id=sess.id,
            status=status,
        )
        session.add(signup)
        signups.append(signup)

    await session.flush()
    return signups
