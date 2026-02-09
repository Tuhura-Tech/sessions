"""Calendar controller for session ICS feeds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event
from litestar import Controller, Response, get
from litestar.enums import MediaType
from litestar.exceptions import NotFoundException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import models as m

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CalendarController(Controller):
    """Public calendar subscription endpoints for sessions."""

    path = "/api/v1/calendar"
    tags = ["calendar"]

    @get(
        "/session/{session_id:uuid}",
        media_type=MediaType.TEXT,
        summary="ICS Calendar Feed for Session",
        description="Subscribe to a live calendar feed for all occurrences of a specific session. Import this URL into your calendar app (Google Calendar, Apple Calendar, Outlook, etc.) to automatically receive updates.",
        cache=False,
    )
    async def get_session_calendar_feed(
        self,
        db_session: AsyncSession,
        session_id: UUID,
    ) -> Response[str]:
        """Generate ICS calendar feed for a specific session.

        Returns an iCalendar (.ics) file containing all non-cancelled occurrences
        for the specified session across all blocks. The feed includes:
        - Session name and location
        - Start and end times
        - Session details and prerequisites
        - Automatic updates when synced with calendar apps

        The feed only includes non-cancelled occurrences and is updated whenever
        occurrences are added, removed, or cancelled.

        Args:
            session_id: UUID of the session to generate calendar for

        Returns:
            ICS calendar file as plain text

        Raises:
            NotFoundException: If session does not exist
        """
        # Fetch the session with location and occurrences
        stmt = (
            select(m.Session)
            .where(m.Session.id == session_id)
            .options(
                joinedload(m.Session.location),
                joinedload(m.Session.occurrences),
            )
        )

        result = await db_session.execute(stmt)
        session = result.unique().scalar_one_or_none()

        if not session:
            raise NotFoundException(detail=f"Session {session_id} not found")

        # Create calendar
        cal = Calendar()
        cal.add("prodid", "-//Tūhura Tech Sessions//Calendar Feed//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", f"Tūhura - {session.name}")
        cal.add("x-wr-timezone", "Pacific/Auckland")
        cal.add("x-wr-caldesc", f"All occurrences of {session.name}")

        # Filter to non-cancelled occurrences (all of them, not just future)
        filtered_occurrences = [occ for occ in session.occurrences if not occ.cancelled]

        # Create events for each occurrence
        for occurrence in filtered_occurrences:
            event = Event()

            # Required fields
            event.add(
                "uid",
                f"tuhura-session-{session.id}-occ-{occurrence.id}@tuhuratech.org.nz",
            )
            event.add("dtstamp", datetime.now(timezone.utc))

            # Convert times to Auckland timezone for proper display
            # The occurrences are stored in UTC, convert to NZST/NZDT for display
            auckland_tz = ZoneInfo("Pacific/Auckland")
            starts_at_nz = occurrence.starts_at.astimezone(auckland_tz)
            ends_at_nz = occurrence.ends_at.astimezone(auckland_tz)

            event.add("dtstart", starts_at_nz)
            event.add("dtend", ends_at_nz)

            # Summary (title)
            event.add("summary", session.name)

            # Description
            description_parts = [
                f"Session: {session.name}",
            ]

            if session.prerequisites:
                description_parts.append(f"Prerequisites: {session.prerequisites}")

            if session.what_to_bring:
                description_parts.append(f"What to bring: {session.what_to_bring}")

            # Location
            location = session.location
            location_str = location.name
            if location.address:
                location_str += f", {location.address}"
            event.add("location", location_str)

            description_parts.append(f"Location: {location_str}")

            event.add("description", "\n\n".join(description_parts))

            # Add geo coordinates if available
            if location.lat and location.lng:
                event.add("geo", (location.lat, location.lng))

            # Categories and status
            event.add("status", "CONFIRMED")
            event.add("transp", "OPAQUE")  # Show as busy

            # Add last modified timestamp
            event.add("last-modified", occurrence.updated_at or occurrence.created_at)

            # Add organizer
            event.add("organizer", "Tūhura Tech <sessions@tuhuratech.org.nz>")

            # Add alarm (reminder) 1 day before
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"Reminder: {session.name} tomorrow")
            alarm.add("trigger", timedelta(days=-1))  # 1 day before
            event.add_component(alarm)

            cal.add_component(event)

        # Generate ICS content
        ics_content = cal.to_ical().decode("utf-8")

        # Return response with proper headers for calendar subscription
        # Use RFC 5987 encoding for filename to support UTF-8 characters (e.g., ū in Tūhura)
        safe_filename = quote(
            f"tuhura-{session.name.lower().replace(' ', '-')}.ics".encode("utf-8")
        )
        return Response(
            content=ics_content,
            media_type=MediaType.TEXT,
            headers={
                "Content-Type": "text/calendar; charset=utf-8; method=PUBLISH",
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}; filename=tuhura-sessions.ics",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-WR-CALNAME": "Tuhura Sessions",
            },
        )


class LegacyCalendarRedirectController(Controller):
    """Redirect legacy session calendar URLs to the new calendar feed."""

    path = "/api/v1/session"
    tags = ["calendar"]

    @get(
        "/{session_id:uuid}/calendar.ic",
        summary="Legacy calendar feed redirect",
        description="Redirect legacy calendar feed URLs to the new calendar subscription endpoint.",
        cache=False,
    )
    async def redirect_calendar_feed(self, session_id: UUID) -> Response[None]:
        return Response(
            content=None,
            status_code=302,
            headers={"Location": f"/api/v1/calendar/session/{session_id}"},
        )

    @get(
        "/{session_id:uuid}/calendar.ics",
        summary="Legacy calendar feed redirect",
        description="Redirect legacy calendar feed URLs to the new calendar subscription endpoint.",
        cache=False,
    )
    async def redirect_calendar_feed_ics(self, session_id: UUID) -> Response[None]:
        return Response(
            content=None,
            status_code=302,
            headers={"Location": f"/api/v1/calendar/session/{session_id}"},
        )
