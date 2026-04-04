from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from litestar import Controller, get
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domains.public.controllers._session_listing import (
    build_session_list_response,
    validate_limit_offset,
)
from app.domains.public.schemas.occurrence import Occurrence
from app.domains.public.schemas.session import (
    BlockOccurrences,
    Location,
    Session,
    SessionDetail,
)
from app.domains.public.services.session import SessionService

logger = logging.getLogger(__name__)


class SessionController(Controller):
    """Public endpoints for caregivers (no auth required)."""

    path = "/api/v1/sessions"
    tags = ["Public"]
    dependencies = providers.create_service_dependencies(
        SessionService,
        "sessions_service",
        load=[
            selectinload(m.Session.location).options(
                joinedload(m.Location.sessions, innerjoin=True)
            ),
            selectinload(m.Session.block_links).selectinload(m.BlockLink.block),
            selectinload(m.Session.occurrences).selectinload(m.Occurrence.block),
            selectinload(m.Session.signups),
        ],
    )

    @get("/", status_code=HTTP_200_OK, summary="List sessions")
    async def list_sessions(
        self,
        sessions_service: SessionService,
        db_session: AsyncSession,
        limit: int | None = None,
        offset: int | None = None,
    ) -> service.OffsetPagination[Session]:
        """List active public sessions sorted by region.

        Returns only non-archived sessions with their block associations.
        """
        validate_limit_offset(limit, offset)
        return await build_session_list_response(
            sessions_service=sessions_service,
            db_session=db_session,
            filters=[m.Session.archived.is_(False), m.Session.session_type != "event"],
            limit=limit,
            offset=offset,
        )

    @get("/{session_id:uuid}", status_code=HTTP_200_OK, summary="Get session")
    async def get_session(
        self,
        sessions_service: SessionService,
        session_id: UUID,
        db_session: AsyncSession,
    ) -> SessionDetail:
        """Fetch a session with public details."""
        from advanced_alchemy.exceptions import NotFoundError

        try:
            result = await db_session.execute(
                select(m.Session)
                .options(
                    selectinload(m.Session.location),
                    selectinload(m.Session.block_links).selectinload(m.BlockLink.block),
                    selectinload(m.Session.occurrences).selectinload(
                        m.Occurrence.block
                    ),
                    selectinload(m.Session.signups),
                )
                .where(m.Session.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session is None:
                raise NotFoundException(detail="Session not found")
        except NotFoundError as exc:
            raise NotFoundException(detail="Session not found") from exc

        if session.archived:
            raise NotFoundException(detail="Session not found")

        # Build blocks list (string names)
        blocks = [block.name for block in session.blocks]

        # Build location schema
        location = Location(
            name=session.location.name,
            address=session.location.address,
            region=session.location.region,
            lat=session.location.lat,
            lng=session.location.lng,
        )

        # Build occurrences_by_block structure
        occurrences_by_block = []
        if session.block_links:
            for block_link in session.block_links:
                block = block_link.block
                # Get all occurrences for this block
                block_occurrences = [
                    o for o in session.occurrences if o.block_id == block.id
                ]
                if block_occurrences:
                    block_occ_schema = BlockOccurrences(
                        block_id=block.id,
                        block_name=block.name,
                        block_type=block.block_type,
                        occurrences=[
                            sessions_service.to_schema(o, schema_type=Occurrence)
                            for o in block_occurrences
                        ],
                    )
                    occurrences_by_block.append(block_occ_schema)

        # Build occurrences list (flat)
        occurrences = [
            sessions_service.to_schema(o, schema_type=Occurrence)
            for o in session.occurrences
        ]

        # Build SessionDetail manually with properly formatted data
        return SessionDetail(
            id=session.id,
            name=session.name,
            year=session.year,
            session_type=session.session_type,
            age_lower=session.age_lower,
            age_upper=session.age_upper,
            day_of_week=session.day_of_week,
            start_time=session.start_time,
            end_time=session.end_time,
            waitlist=getattr(session, "is_full", False),
            description=session.description,
            blocks=blocks,
            location=location,
            occurrences=occurrences,
            occurrences_by_block=occurrences_by_block,
        )
