from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from litestar import Controller, get
from litestar.exceptions import NotFoundException, ValidationException
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.db.models.block import Block as BlockModel
from app.db.models.block_link import BlockLink as BlockLinkModel
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
        if limit is not None and limit < 0:
            raise ValidationException(detail="limit must be >= 0")
        if offset is not None and offset < 0:
            raise ValidationException(detail="offset must be >= 0")

        filters = [m.Session.archived.is_(False)]
        if limit is not None or offset is not None:
            from advanced_alchemy.filters import LimitOffset

            filters.append(LimitOffset(limit=limit or 0, offset=offset or 0))

        results, total = await sessions_service.list_and_count(*filters)

        blocks_by_session = defaultdict(list)
        if results:
            block_res = await db_session.execute(
                select(BlockLinkModel.session_id, BlockModel.name)
                .join(BlockModel, BlockModel.id == BlockLinkModel.block_id)
                .where(BlockLinkModel.session_id.in_([s.id for s in results]))
            )
            for session_id, block_name in block_res.all():
                blocks_by_session[str(session_id)].append(block_name)

        schemas = []
        for result in results:
            location = Location(
                name=result.location.name,
                address=result.location.address,
                region=result.location.region,
                lat=result.location.lat,
                lng=result.location.lng,
            )
            schema = Session(
                id=result.id,
                name=result.name,
                year=result.year,
                age_lower=result.age_lower,
                age_upper=result.age_upper,
                day_of_week=result.day_of_week,
                start_time=result.start_time,
                end_time=result.end_time,
                what_to_bring=result.what_to_bring,
                prerequisites=result.prerequisites,
                blocks=blocks_by_session.get(str(result.id), []),
                location=location,
            )
            schemas.append(schema)

        return service.OffsetPagination(
            items=schemas,
            limit=limit or 0,
            offset=offset or 0,
            total=total,
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
        schema = SessionDetail(
            id=session.id,
            name=session.name,
            year=session.year,
            age_lower=session.age_lower,
            age_upper=session.age_upper,
            day_of_week=session.day_of_week,
            start_time=session.start_time,
            end_time=session.end_time,
            what_to_bring=session.what_to_bring,
            prerequisites=session.prerequisites,
            blocks=blocks,
            location=location,
            occurrences=occurrences,
            occurrences_by_block=occurrences_by_block,
        )
        return schema
