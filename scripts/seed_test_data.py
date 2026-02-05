#!/usr/bin/env python3
"""
Seed test data for E2E tests.
Creates minimal test data: locations, blocks (terms), and sessions.
"""

import asyncio
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment before imports
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://sessions:9e58291888cd07815ac8c03791377f39e857154c0c9fadcf9670b657fb487644e32064d624b1734f5f84fd43edb2c04a99b24e2b2c53c75528f2f029d73a36bd@localhost:5432/sessions",
)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import models as m


async def seed_test_data():
    """Seed database with minimal test data."""
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clean up existing test data
        print("Cleaning up existing test data...")
        await session.execute(m.Signup.__table__.delete())
        await session.execute(m.Occurrence.__table__.delete())
        await session.execute(m.Session.__table__.delete())
        await session.execute(m.ExclusionDate.__table__.delete())
        await session.execute(m.Block.__table__.delete())
        await session.execute(m.Location.__table__.delete())
        await session.commit()

        # Create test locations
        print("Creating test locations...")
        location1 = m.Location(
            name="Test School A",
            address="123 Test Street, Auckland",
            region="Auckland",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@testschool.nz",
            contact_phone="021 123 4567",
        )
        location2 = m.Location(
            name="Test Community Center",
            address="456 Community Road, Wellington",
            region="Wellington",
            lat=-41.2865,
            lng=174.7762,
            contact_name="Jane Doe",
            contact_email="jane@community.nz",
            contact_phone="021 987 6543",
        )
        session.add_all([location1, location2])
        await session.flush()

        # Create test blocks (terms)
        print("Creating test blocks (terms)...")
        current_year = datetime.now().year

        term1 = m.Block(
            year=current_year,
            name="Term 1",
            start_date=datetime(current_year, 2, 1).date(),
            end_date=datetime(current_year, 4, 15).date(),
        )
        term2 = m.Block(
            year=current_year,
            name="Term 2",
            start_date=datetime(current_year, 5, 1).date(),
            end_date=datetime(current_year, 7, 10).date(),
        )
        special = m.Block(
            year=current_year,
            name="Summer Bootcamp",
            start_date=datetime(current_year, 12, 15).date(),
            end_date=datetime(current_year, 12, 22).date(),
        )
        session.add_all([term1, term2, special])
        await session.flush()

        # Create test sessions
        print("Creating test sessions...")

        # Create BlockLinks for sessions
        block_link1 = m.BlockLink(
            session_id=None, block_id=term1.id
        )  # Will set session_id after flush
        block_link2 = m.BlockLink(session_id=None, block_id=term1.id)
        block_link3 = m.BlockLink(session_id=None, block_id=term2.id)

        session1 = m.Session(
            location_id=location1.id,
            year=current_year,
            session_type="term",
            name="Introduction to Python",
            age_lower=8,
            age_upper=12,
            day_of_week=1,  # Monday
            start_time=time(14, 0),
            end_time=time(15, 30),
            capacity=15,
        )

        session2 = m.Session(
            location_id=location2.id,
            year=current_year,
            session_type="term",
            name="Web Development Workshop",
            age_lower=10,
            age_upper=14,
            day_of_week=3,  # Wednesday
            start_time=time(15, 0),
            end_time=time(16, 30),
            capacity=12,
        )

        session3 = m.Session(
            location_id=location1.id,
            year=current_year,
            session_type="term",
            name="Game Design Basics",
            age_lower=9,
            age_upper=13,
            day_of_week=2,  # Tuesday
            start_time=time(14, 30),
            end_time=time(16, 0),
            capacity=20,
        )

        session.add_all([session1, session2, session3])
        await session.flush()

        # Now set session_ids on block_links
        block_link1.session_id = session1.id
        block_link2.session_id = session2.id
        block_link3.session_id = session3.id
        session.add_all([block_link1, block_link2, block_link3])
        await session.flush()

        # Create occurrences for sessions
        print("Creating session occurrences...")
        for sess in [session1, session2, session3]:
            # Get the block via block_link
            result = await session.execute(
                m.BlockLink.__table__.select().where(m.BlockLink.session_id == sess.id)
            )
            block_link = result.first()
            if not block_link:
                continue

            block = await session.get(m.Block, block_link.block_id)

            # Generate occurrences for the first 4 weeks
            current_date = datetime.combine(block.start_date, sess.start_time)
            end_date = datetime.combine(block.end_date, sess.end_time)
            occurrence_count = 0

            while current_date <= end_date and occurrence_count < 4:
                # Check if this date matches the session's day of week
                if current_date.weekday() == sess.day_of_week:
                    starts_at = current_date
                    ends_at = datetime.combine(current_date.date(), sess.end_time)

                    occurrence = m.Occurrence(
                        session_id=sess.id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        cancelled=False,
                        block_id=block.id,
                    )
                    session.add(occurrence)
                    occurrence_count += 1

                current_date += timedelta(days=1)

        # Create caregiver, student, and confirmed signup for attendance roll
        print("Creating test caregiver/student/signup...")
        caregiver = m.Caregiver(
            name="Test Guardian",
            email="guardian@example.com",
            phone="021 555 0000",
            email_verified=True,
        )
        session.add(caregiver)
        await session.flush()

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=datetime(current_year - 10, 6, 15).date(),
            region="Auckland",
            school_name="Test School A",
        )
        session.add(student)
        await session.flush()

        signup = m.Signup(
            session_id=session1.id,
            student_id=student.id,
            status="confirmed",
            needs_devices=False,
        )
        session.add(signup)

        await session.commit()

        print("\n✅ Test data seeded successfully!")
        print("   - 2 locations")
        print("   - 3 blocks (terms)")
        print("   - 3 sessions")
        print("   - ~12 occurrences")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_test_data())
