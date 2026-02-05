from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import AsyncIterator
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, get, patch, post
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

    @get("/{session_id:uuid}")
    async def get_session(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> Session:
        """Get a single session by ID."""
        session = await session_service.get(session_id)
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

        exclusions = await session_service.exclusions.list()

        filtered_exclusions = [
            e.date for e in exclusions if e.date.year == session.year
        ]
        for block in blocks:
            day = block.start_date
            # Convert enum to int for arithmetic (day_of_week is DayOfWeekEnum | None)
            day_of_week_int = (
                int(session.day_of_week) if session.day_of_week is not None else 0
            )
            days_ahead = (day_of_week_int - day.weekday() + 7) % 7
            day = day + timedelta(days=days_ahead)

            while day <= block.end_date:
                if day not in filtered_exclusions:
                    await session_service.occurrences.create(
                        m.Occurrence(
                            session_id=session.id,
                            block_id=block.id,
                            starts_at=datetime.combine(day, session.start_time),
                            ends_at=datetime.combine(day, session.end_time),
                        )
                    )
                day += timedelta(weeks=1)

        return session_service.to_schema(session, schema_type=Session)

    @patch("/{session_id:uuid}")
    async def update_session(
        self,
        session_id: UUID,
        data: SessionUpdate,
        session_service: SessionService,
    ) -> Session:
        """Update an existing session."""
        session = await session_service.update(
            data.model_dump(exclude_unset=True), session_id
        )
        if not session:
            raise NotFoundException(detail="Session not found")
        return session_service.to_schema(session, schema_type=Session)

    @post("/{session_id:uuid}/email", status_code=HTTP_200_OK)
    async def email_session(
        self, session_id: UUID, session_service: SessionService, data: SessionEmail
    ) -> None:
        """Email session details to participants."""

        # queue = await get_task_queue()
        # await queue.enqueue(
        #     "email_session",
        #     session_id=session_id,
        #     title=data.title,
        #     body=data.body,
        # )
        pass

    @get("/{session_id:uuid}/occurrences", status_code=HTTP_200_OK)
    async def get_occurrences(
        self,
        session_id: UUID,
        session_service: SessionService,
    ) -> service.OffsetPagination[Occurrence]:
        """Get occurrences for a session with eager loading to avoid N+1 queries."""
        session = await session_service.get(session_id)
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
