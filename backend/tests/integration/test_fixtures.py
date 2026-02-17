"""
Integration test fixtures and utilities for endpoint testing.

Provides shared fixtures for all endpoint tests including database sessions,
test client, and helper functions for common test operations.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Block,
    Caregiver,
    ExclusionDate,
    Session as SessionModel,
    Location,
    Student,
    CaregiverMagicLink,
    CaregiverSession,
)
from app.lib.auth import (
    new_token,
    hash_token,
    magic_link_expires_at,
    session_expires_at,
)


# ============================================================================
# Helper Functions
# ============================================================================


async def create_test_caregiver(
    db_session: AsyncSession,
    email: str = "test@example.com",
    name: str = "Test User",
) -> Caregiver:
    """Create a test caregiver."""
    caregiver = Caregiver(email=email, name=name)
    db_session.add(caregiver)
    await db_session.flush()
    await db_session.commit()
    return caregiver


async def create_test_location(
    db_session: AsyncSession,
    name: str = "Test Location",
    address: str = "123 Test St",
    region: str = "Test Region",
    lat: float = -41.2865,
    lng: float = 174.7762,
    contact_name: str = "Test Contact",
    contact_email: str = "contact@example.com",
) -> Location:
    """Create a test location."""
    location = Location(
        name=name,
        address=address,
        region=region,
        lat=lat,
        lng=lng,
        contact_name=contact_name,
        contact_email=contact_email,
    )
    db_session.add(location)
    await db_session.flush()
    await db_session.commit()
    return location


async def create_test_block(
    db_session: AsyncSession,
    year: int = 2026,
    name: str = "Test Block",
    block_type: str = "special",
    start_date: str | None = None,
    end_date: str | None = None,
) -> Block:
    """Create a test block."""
    from datetime import date

    if not start_date:
        start_date = date(year, 1, 15)
    if not end_date:
        end_date = date(year, 3, 31)

    block = Block(
        year=year,
        name=name,
        block_type=block_type,
        start_date=start_date,
        end_date=end_date,
    )
    db_session.add(block)
    await db_session.flush()
    await db_session.commit()
    return block


async def create_test_session(
    db_session: AsyncSession,
    location: Location | None = None,
    name: str = "Test Session",
    year: int = 2026,
    age_lower: int = 5,
    age_upper: int = 12,
    session_type: str = "special",
    day_of_week: int | None = None,
    archived: bool = False,
    capacity: int = 20,
) -> SessionModel:
    """Create a test session."""
    from datetime import time

    if not location:
        location = await create_test_location(db_session)

    # Default day_of_week to 1 (Monday) if not provided
    if day_of_week is None:
        day_of_week = 1

    session = SessionModel(
        name=name,
        location_id=location.id,
        year=year,
        age_lower=age_lower,
        age_upper=age_upper,
        session_type=session_type,
        day_of_week=day_of_week,
        start_time=time(9, 0),
        end_time=time(17, 0),
        capacity=capacity,
        archived=archived,
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.commit()
    return session


async def create_test_student(
    db_session: AsyncSession,
    caregiver: Caregiver | None = None,
    name: str = "Test Student",
) -> Student:
    """Create a test student."""
    if not caregiver:
        caregiver = await create_test_caregiver(db_session)

    from datetime import date, timedelta

    student = Student(
        caregiver_id=caregiver.id,
        name=name,
        date_of_birth=date.today() - timedelta(days=365 * 10),
    )
    db_session.add(student)
    await db_session.flush()
    await db_session.commit()
    return student


async def create_test_exclusion_date(
    db_session: AsyncSession,
    date: date | None = None,
    year: int | None = None,
    reason: str = "Holiday",
) -> ExclusionDate:
    """Create a test exclusion date."""
    from datetime import date as date_type
    from app.db import models as m

    if not date:
        date = date_type(2025, 12, 25)

    # Extract year from date if not provided
    if not year:
        year = date.year

    exclusion = m.ExclusionDate(year=year, date=date, reason=reason)
    db_session.add(exclusion)
    await db_session.flush()
    await db_session.commit()
    return exclusion


async def create_magic_link(
    db_session: AsyncSession,
    caregiver: Caregiver,
) -> tuple[str, CaregiverMagicLink]:
    """Create a magic link for testing.

    Returns the token and the magic link model.
    """
    token = new_token()
    magic_link = CaregiverMagicLink(
        caregiver_id=caregiver.id,
        token_hash=hash_token(token),
        expires_at=magic_link_expires_at(),
    )
    db_session.add(magic_link)
    await db_session.flush()
    await db_session.commit()
    return token, magic_link


async def create_session_cookie(
    db_session: AsyncSession,
    caregiver: Caregiver,
) -> tuple[str, CaregiverSession]:
    """Create a session cookie for testing.

    Returns the token and the session model.
    """
    token = new_token()
    session = CaregiverSession(
        caregiver_id=caregiver.id,
        token_hash=hash_token(token),
        expires_at=session_expires_at(),
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.commit()
    return token, session
