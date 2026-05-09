from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from io import StringIO
from typing import AsyncIterator
from uuid import UUID

from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError
from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, delete, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.response import Stream
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.occurrence import Occurrence
from app.domains.admin.schemas.session import (
    Session,
    SessionCreate,
    SessionEmail,
    SessionUpdate,
)
from app.domains.admin.schemas.signup import Signup
from app.domains.admin.schemas.staff import StaffSessionSummary
from app.domains.admin.services.session import SessionService

logger = logging.getLogger(__name__)


class SessionController(Controller):
    """Admin endpoints for managing sessions."""

    path = "/api/v1/admin/sessions"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        SessionService,
        "session_service",
        load=[
            selectinload(m.Session.location).options(
                joinedload(m.Location.sessions, innerjoin=True)
            ),
            selectinload(m.Session.signups),
            selectinload(m.Session.block_links),
        ],
    )

    @get("/")
    async def list_sessions(
        self,
        session_service: SessionService,
        limit: int = 100,
        offset: int = 0,
    ) -> service.OffsetPagination[Session]:
        """List all sessions with pagination.

        Args:
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)
        """
        results, total = await session_service.list_and_count(
            LimitOffset(limit, offset)
        )
        return session_service.to_schema(results, total, schema_type=Session)

    @get("/unassigned")
    async def list_unassigned_sessions(
        self,
        session_service: SessionService,
    ) -> list[StaffSessionSummary]:
        """List all sessions that have no staff assigned.

        Returns sessions that don't have any staff members assigned to them,
        useful for identifying scheduling gaps.
        """
        # Subquery to find sessions with staff
        sessions_with_staff = select(m.SessionStaff.session_id).distinct()

        # Get all sessions that are NOT in the subquery
        stmt = (
            select(m.Session)
            .where(m.Session.id.notin_(sessions_with_staff))
            .options(selectinload(m.Session.location))
            .order_by(
                m.Session.year.desc(), m.Session.day_of_week, m.Session.start_time
            )
        )

        result = await session_service.repository.session.execute(stmt)
        sessions = result.scalars().unique().all()

        return [
            StaffSessionSummary(
                id=session.id,
                name=session.name,
                year=session.year,
                session_type=session.session_type,
                day_of_week=session.day_of_week,
                start_time=str(session.start_time) if session.start_time else None,
                end_time=str(session.end_time) if session.end_time else None,
                location_name=session.location.name if session.location else None,
            )
            for session in sessions
        ]

    @get("/{session_id:uuid}")
    async def get_session(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> Session:
        """Get a single session by ID."""
        try:
            session = await session_service.get(session_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Session not found")
        if not session:
            raise NotFoundException(detail="Session not found")
        return session_service.to_schema(session, schema_type=Session)

    @post("/")
    async def create_session(
        self,
        data: SessionCreate,
        session_service: SessionService,
    ) -> Session:
        """Create a new session."""
        session = await session_service.create(data)

        # Add block links
        blocks: list[m.Block] = []
        for block in data.blocks:
            await session_service.session_block_service.create(
                m.BlockLink(session_id=session.id, block_id=block)
            )

            blocks.append(await session_service.blocks.get(block))

        if session.session_type != "special" and data.generate_occurrences:
            exclusions = await session_service.exclusions.list()

            filtered_exclusions = [
                e.date for e in exclusions if e.date.year == session.year
            ]
            local_tz = ZoneInfo("Pacific/Auckland")
            for block in blocks:
                day = block.start_date
                # Convert enum to int for arithmetic (day_of_week is DayOfWeekEnum | None)
                day_of_week_int = (
                    int(session.day_of_week) if session.day_of_week is not None else 0
                )
                # Convert DayOfWeekEnum (0=Sun..6=Sat) to Python weekday (0=Mon..6=Sun)
                day_of_week_python = (day_of_week_int - 1) % 7
                days_ahead = (day_of_week_python - day.weekday() + 7) % 7
                day = day + timedelta(days=days_ahead)

                while day <= block.end_date:
                    if day not in filtered_exclusions:
                        starts_at_local = datetime.combine(
                            day, session.start_time, tzinfo=local_tz
                        )
                        ends_at_local = datetime.combine(
                            day, session.end_time, tzinfo=local_tz
                        )
                        await session_service.occurrences.create(
                            m.Occurrence(
                                session_id=session.id,
                                block_id=block.id,
                                starts_at=starts_at_local.astimezone(timezone.utc),
                                ends_at=ends_at_local.astimezone(timezone.utc),
                            )
                        )
                    day += timedelta(weeks=1)

        # Refresh the session to load relationships
        session = await session_service.get(session.id)
        return session_service.to_schema(session, schema_type=Session)

    @patch("/{session_id:uuid}")
    async def update_session(
        self,
        session_id: UUID,
        data: SessionUpdate,
        session_service: SessionService,
    ) -> Session:
        """Update an existing session."""
        update_payload = data.model_dump(exclude_unset=True)

        # Extract blocks before passing to the ORM update (not a model column)
        new_block_ids: list[UUID] | None = update_payload.pop("blocks", None)

        reschedule_fields = {"day_of_week", "start_time", "end_time"}
        should_reschedule = bool(reschedule_fields.intersection(update_payload.keys()))

        try:
            session = await session_service.update(update_payload, session_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Session not found")
        if not session:
            raise NotFoundException(detail="Session not found")

        db = session_service.repository.session

        # --- Block link reconciliation ---
        if new_block_ids is not None:
            # Fetch current links fresh from DB
            existing_links_result = await db.execute(
                select(m.BlockLink).where(m.BlockLink.session_id == session_id)
            )
            existing_links = existing_links_result.scalars().all()
            existing_block_ids = {link.block_id for link in existing_links}
            desired_block_ids = set(new_block_ids)

            # Delete links for blocks no longer selected
            for link in existing_links:
                if link.block_id not in desired_block_ids:
                    await session_service.session_block_service.delete(link.id)

            # Add links for newly selected blocks
            for block_id in desired_block_ids - existing_block_ids:
                await session_service.session_block_service.create(
                    m.BlockLink(session_id=session_id, block_id=block_id)
                )

            # Flush so the DB reflects the new block links before we query occurrences
            await db.flush()

            should_reschedule = True

        # --- Occurrence reschedule ---
        if should_reschedule and session.session_type == "term":
            # Re-fetch session fields (day_of_week, start_time, end_time)
            session = await session_service.get(session_id)
            if not session:
                raise NotFoundException(detail="Session not found")

            exclusions = await session_service.exclusions.list()
            filtered_exclusions = [
                e.date for e in exclusions if e.date.year == session.year
            ]
            local_tz = ZoneInfo("Pacific/Auckland")

            # Fetch active block links fresh from DB (after flush)
            active_links_result = await db.execute(
                select(m.BlockLink).where(m.BlockLink.session_id == session_id)
            )
            active_links = active_links_result.scalars().all()
            active_block_ids = {link.block_id for link in active_links}

            # Delete all occurrences for blocks no longer linked (fresh DB query)
            old_occs_result = await db.execute(
                select(m.Occurrence).where(
                    m.Occurrence.session_id == session_id,
                    m.Occurrence.block_id.notin_(active_block_ids)
                    if active_block_ids
                    else m.Occurrence.block_id.isnot(None),
                )
            )
            for occ in old_occs_result.scalars().all():
                await session_service.occurrences.delete(occ.id)

            await db.flush()

            # Recalculate occurrences for each active block
            for link in active_links:
                block = await session_service.blocks.get(link.block_id)
                if not block:
                    continue

                day = block.start_date
                day_of_week_int = (
                    int(session.day_of_week) if session.day_of_week is not None else 0
                )
                day_of_week_python = (day_of_week_int - 1) % 7
                days_ahead = (day_of_week_python - day.weekday() + 7) % 7
                day = day + timedelta(days=days_ahead)

                desired_dates: list = []
                while day <= block.end_date:
                    if day not in filtered_exclusions:
                        desired_dates.append(day)
                    day += timedelta(weeks=1)

                # Fetch existing occurrences for this block fresh from DB
                existing_occs_result = await db.execute(
                    select(m.Occurrence)
                    .where(
                        m.Occurrence.session_id == session_id,
                        m.Occurrence.block_id == block.id,
                    )
                    .order_by(m.Occurrence.starts_at)
                )
                occurrences = existing_occs_result.scalars().all()

                for index, occ_day in enumerate(desired_dates):
                    starts_at_local = datetime.combine(
                        occ_day, session.start_time, tzinfo=local_tz
                    )
                    ends_at_local = datetime.combine(
                        occ_day, session.end_time, tzinfo=local_tz
                    )
                    starts_at = starts_at_local.astimezone(timezone.utc)
                    ends_at = ends_at_local.astimezone(timezone.utc)

                    if index < len(occurrences):
                        await session_service.occurrences.update(
                            {
                                "starts_at": starts_at,
                                "ends_at": ends_at,
                                "cancelled": False,
                                "cancellation_reason": None,
                            },
                            occurrences[index].id,
                        )
                    else:
                        await session_service.occurrences.create(
                            m.Occurrence(
                                session_id=session_id,
                                block_id=block.id,
                                starts_at=starts_at,
                                ends_at=ends_at,
                            )
                        )

                for extra in occurrences[len(desired_dates) :]:
                    await session_service.occurrences.delete(extra.id)

        session = await session_service.get(session_id)
        return session_service.to_schema(session, schema_type=Session)

    @delete("/{session_id:uuid}", status_code=HTTP_200_OK)
    async def delete_session(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> None:
        """Delete a session."""
        try:
            await session_service.delete(session_id)
        except AlchemyNotFoundError as exc:
            raise NotFoundException(detail="Session not found") from exc

    @post("/{session_id:uuid}/email", status_code=HTTP_200_OK)
    async def email_session(
        self, session_id: UUID, session_service: SessionService, data: SessionEmail
    ) -> dict[str, int]:
        """Email session details to participants."""
        from app.lib.deps import get_task_queue
        from sqlalchemy import func

        # Count confirmed signups for this session
        result = await session_service.signups.repository.session.execute(
            select(func.count())
            .select_from(m.Signup)
            .where(m.Signup.session_id == session_id, m.Signup.status == "confirmed")
        )
        enqueued = result.scalar_one()

        # Enqueue the bulk email task
        queue = await get_task_queue()
        await queue.enqueue(
            "send_session_bulk_email_task",
            session_id=str(session_id),
            subject=data.subject,
            message=data.message,
        )

        return {"enqueued": enqueued}

    @get("/{session_id:uuid}/occurrences", status_code=HTTP_200_OK)
    async def get_occurrences(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> service.OffsetPagination[Occurrence]:
        """Get occurrences for a session with eager loading to avoid N+1 queries."""
        try:
            session = await session_service.get(session_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Session not found")
        if not session:
            raise NotFoundException(detail="Session not found")

        # Eager load related data to avoid N+1 queries
        occurrences = await session_service.occurrences.list(
            m.Occurrence.session_id == session_id,
            load=[
                selectinload(m.Occurrence.session),
                selectinload(m.Occurrence.block),
            ],
        )
        return session_service.occurrences.to_schema(
            occurrences, schema_type=Occurrence
        )

    @get("/{session_id:uuid}/signups", status_code=HTTP_200_OK)
    async def get_signups(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> service.OffsetPagination[Signup]:
        """Get signups for a session."""
        session = await session_service.get(session_id)
        if not session:
            raise NotFoundException(detail="Session not found")
        signups = await session_service.signups.list(
            m.Signup.session_id == session_id,
            load=[
                selectinload(m.Signup.student).selectinload(m.Student.caregiver),
            ],
        )
        return session_service.signups.to_schema(signups, schema_type=Signup)

    @get("/{session_id:uuid}/export/signups.csv")
    async def export_signups_csv(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> Stream:
        """Export session signups as a streaming CSV file.

        Includes student details, caregiver information, and signup status.
        Uses streaming to efficiently handle large datasets.
        """
        session = await session_service.get(session_id)
        if not session:
            raise NotFoundException(detail="Session not found")

        async def generate_csv() -> AsyncIterator[str]:
            """Generate CSV content as an async iterator."""
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "Signup ID",
                    "Student Name",
                    "Date of Birth",
                    "Caregiver Name",
                    "Email",
                    "Phone",
                    "Status",
                    "Media Consent",
                    "Medical Info",
                    "Needs Devices",
                    "Pickup/Dropoff",
                    "Created At",
                ]
            )
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

            # Get all signups with related data (already optimized with selectinload)
            signups = await session_service.signups.list(
                session_id=session_id,
                load=[
                    selectinload(m.Signup.student).selectinload(m.Student.caregiver),
                ],
            )

            # Stream each row instead of building entire CSV in memory
            for signup in signups:
                writer.writerow(
                    [
                        str(signup.id),
                        signup.student.name,
                        signup.student.date_of_birth.isoformat(),
                        signup.student.caregiver.name,
                        signup.student.caregiver.email,
                        signup.student.caregiver.phone or "",
                        signup.status,
                        "Yes" if signup.student.media_consent else "No",
                        signup.student.medical_info or "",
                        "Yes" if signup.needs_devices else "No",
                        signup.pickup_dropoff or "",
                        signup.created_at.isoformat(),
                    ]
                )
                yield output.getvalue()
                output.truncate(0)
                output.seek(0)

        return Stream(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}_signups.csv"'
            },
        )

    @get("/{session_id:uuid}/export/attendance.csv")
    async def export_attendance_csv(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> Stream:
        """Export session attendance records as a streaming CSV file.

        Includes occurrence details and student attendance status. Uses a single
        optimized query with joins and streaming to efficiently handle large datasets.
        """
        session = await session_service.get(session_id)
        if not session:
            raise NotFoundException(detail="Session not found")

        async def generate_csv() -> AsyncIterator[str]:
            """Generate CSV content as an async iterator."""
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "Occurrence ID",
                    "Occurrence Date",
                    "Starts At",
                    "Ends At",
                    "Student ID",
                    "Student Name",
                    "Status",
                    "Reason",
                    "Marked At",
                ]
            )
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

            # Fetch all data in a single query with proper joins
            stmt = (
                select(m.AttendanceRecord, m.Occurrence, m.Student)
                .join(m.Occurrence, m.AttendanceRecord.occurrence_id == m.Occurrence.id)
                .join(m.Student, m.AttendanceRecord.student_id == m.Student.id)
                .where(m.Occurrence.session_id == session_id)
                .order_by(m.Occurrence.starts_at, m.Student.name)
            )

            result = await session_service.repository.session.execute(stmt)
            records = result.all()

            # Stream each row instead of building entire CSV in memory
            for attendance, occurrence, student in records:
                writer.writerow(
                    [
                        str(occurrence.id),
                        occurrence.starts_at.date().isoformat(),
                        occurrence.starts_at.isoformat(),
                        occurrence.ends_at.isoformat(),
                        str(student.id),
                        student.name,
                        attendance.status,
                        attendance.reason or "",
                        attendance.created_at.isoformat(),
                    ]
                )
                yield output.getvalue()
                output.truncate(0)
                output.seek(0)

        return Stream(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}_attendance.csv"'
            },
        )
