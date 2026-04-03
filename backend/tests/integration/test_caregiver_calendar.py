"""Integration tests for session calendar subscription endpoint."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

from app.db import models as m

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestSessionCalendarEndpoint:
    """Test session calendar subscription endpoint."""

    async def test_calendar_returns_404_for_nonexistent_session(
        self, client: AsyncClient
    ):
        """Test that calendar endpoint returns 404 for non-existent session."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/calendar/session/{fake_uuid}")
        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_calendar_returns_ics_format(self, client: AsyncClient, db_session):
        """Test that calendar endpoint returns valid ICS content."""
        # Create location
        location = m.Location(
            name="Test Center",
            address="123 Test St",
            region="Auckland",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        # Create session
        session = m.Session(
            name="Python Programming",
            location_id=location.id,
            year=2025,
            session_type="term",
            day_of_week=2,  # Tuesday
            start_time=time(14, 0),
            end_time=time(16, 0),
            age_lower=10,
            age_upper=14,
            capacity=10,
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(f"/api/v1/calendar/session/{session.id}")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith("text/calendar")
        assert "VCALENDAR" in response.text
        assert "VERSION:2.0" in response.text
        assert "PRODID:-//Tūhura Tech Sessions//Calendar Feed//EN" in response.text

    async def test_calendar_includes_session_occurrences(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test that calendar includes events for session occurrences."""
        # Create location
        location = m.Location(
            name="Test Center",
            address="123 Test St",
            region="Auckland",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        # Create block
        block = m.Block(
            year=2025,
            name="Term 1",
            block_type="term_1",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 4, 15),
        )
        db_session.add(block)
        await db_session.flush()

        # Create session
        session = m.Session(
            name="Python Programming",
            location_id=location.id,
            year=2025,
            session_type="term",
            day_of_week=2,  # Tuesday
            start_time=time(14, 0),
            end_time=time(16, 0),
            age_lower=10,
            age_upper=14,
            capacity=10,
        )
        db_session.add(session)
        await db_session.flush()

        # Create future occurrence
        future_start = datetime.now(timezone.utc) + timedelta(days=7)
        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=future_start,
            ends_at=future_start + timedelta(hours=2),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.commit()

        # Get calendar feed
        response = await client.get(f"/api/v1/calendar/session/{session.id}")

        assert response.status_code == HTTP_200_OK
        content = response.text

        # Verify calendar structure
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "SUMMARY:Python Programming" in content
        assert "LOCATION:Test Center" in content  # Location is escaped by the library
        assert "123 Test St" in content
        assert "STATUS:CONFIRMED" in content
        assert "END:VEVENT" in content
        assert "END:VCALENDAR" in content

    async def test_calendar_excludes_cancelled_occurrences(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test that calendar excludes cancelled occurrences."""
        # Create location
        location = m.Location(
            name="Test Center",
            address="123 Test St",
            region="Auckland",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        # Create block
        block = m.Block(
            year=2025,
            name="Term 1",
            block_type="term_1",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 4, 15),
        )
        db_session.add(block)
        await db_session.flush()

        # Create session
        session = m.Session(
            name="Python Programming",
            location_id=location.id,
            year=2025,
            session_type="term",
            day_of_week=2,
            start_time=time(14, 0),
            end_time=time(16, 0),
            age_lower=10,
            age_upper=14,
            capacity=10,
        )
        db_session.add(session)
        await db_session.flush()

        # Create cancelled occurrence
        cancelled_start = datetime.now(timezone.utc) + timedelta(days=7)
        cancelled_occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=cancelled_start,
            ends_at=cancelled_start + timedelta(hours=2),
            cancelled=True,
        )
        db_session.add(cancelled_occurrence)
        await db_session.commit()

        # Get calendar feed
        response = await client.get(f"/api/v1/calendar/session/{session.id}")

        assert response.status_code == HTTP_200_OK
        content = response.text

        # Should not contain any events since the occurrence is cancelled
        assert "BEGIN:VEVENT" not in content

    async def test_calendar_includes_session_details(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test that calendar includes session details in event description."""
        # Create location
        location = m.Location(
            name="Test Center",
            address="123 Test St",
            region="Auckland",
            lat=-36.8485,
            lng=174.7633,
            contact_name="Test Contact",
            contact_email="contact@test.com",
        )
        db_session.add(location)
        await db_session.flush()

        # Create block
        block = m.Block(
            year=2025,
            name="Term 1",
            block_type="term_1",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 4, 15),
        )
        db_session.add(block)
        await db_session.flush()

        # Create session with details
        session = m.Session(
            name="Python Programming",
            location_id=location.id,
            year=2025,
            session_type="term",
            day_of_week=2,
            start_time=time(14, 0),
            end_time=time(16, 0),
            age_lower=10,
            age_upper=14,
            capacity=10,
        )
        db_session.add(session)
        await db_session.flush()

        # Create future occurrence
        future_start = datetime.now(timezone.utc) + timedelta(days=7)
        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=future_start,
            ends_at=future_start + timedelta(hours=2),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.commit()

        # Get calendar feed
        response = await client.get(f"/api/v1/calendar/session/{session.id}")

        assert response.status_code == HTTP_200_OK
        content = response.text

        # Verify session details are included
        assert "Python Programming" in content
        assert "BEGIN:VALARM" in content  # Reminder alarm
        assert "TRIGGER:-P1D" in content  # 1 day before
