from __future__ import annotations

from advanced_alchemy.extensions.litestar import providers, service
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domains.public.controllers._session_listing import (
    build_session_list_response,
    validate_limit_offset,
)
from app.domains.public.schemas.session import Session
from app.domains.public.services.session import SessionService


class EventController(Controller):
    """Public event endpoints for caregivers (no auth required)."""

    path = "/api/v1/events"
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

    @get("/", status_code=HTTP_200_OK, summary="List events")
    async def list_events(
        self,
        sessions_service: SessionService,
        db_session: AsyncSession,
        limit: int | None = None,
        offset: int | None = None,
    ) -> service.OffsetPagination[Session]:
        """List active public events sorted by region.

        Returns only non-archived sessions where session_type is event.
        """
        validate_limit_offset(limit, offset)
        return await build_session_list_response(
            sessions_service=sessions_service,
            db_session=db_session,
            filters=[m.Session.archived.is_(False), m.Session.session_type == "event"],
            limit=limit,
            offset=offset,
        )
