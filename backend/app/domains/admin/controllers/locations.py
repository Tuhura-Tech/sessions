from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK

from app.domains.admin.schemas.location import Location, LocationCreate, LocationUpdate
from app.domains.admin.schemas.session import Session
from sqlalchemy.orm import joinedload, selectinload
from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.services.location import LocationService
from app.domains.admin.services.session import SessionService

logger = logging.getLogger(__name__)


class LocationController(Controller):
    """Public endpoints for caregivers (no auth required)."""

    path = "/api/v1/admin/locations"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = {
        **providers.create_service_dependencies(
            LocationService,
            "location_service",
            load=[
                selectinload(m.Location.sessions).options(
                    joinedload(m.Session.location),
                    selectinload(m.Session.signups),
                )
            ],
        ),
        **providers.create_service_dependencies(
            SessionService,
            "session_service",
            load=[
                selectinload(m.Session.location),
                selectinload(m.Session.signups),
            ],
        ),
    }

    @get("/", status_code=HTTP_200_OK, summary="List locations")
    async def list_locations(
        self,
        location_service: LocationService,
        limit: int = 100,
        offset: int = 0,
    ) -> service.OffsetPagination[Location]:
        """List all locations with pagination.

        Args:
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)
        """
        results, total = await location_service.list_and_count(
            LimitOffset(limit, offset)
        )
        return location_service.to_schema(results, total, schema_type=Location)

    @post("/")
    async def create_location(
        self,
        location_service: LocationService,
        data: LocationCreate,
    ) -> Location:
        """Create a new location."""
        loc = await location_service.create(data)
        return location_service.to_schema(loc, schema_type=Location)

    @get("/{location_id:uuid}", status_code=HTTP_200_OK, summary="Get location by ID")
    async def get_location(
        self,
        location_service: LocationService,
        location_id: UUID,
    ) -> Location:
        """Get a specific location by ID."""
        loc = await location_service.get(location_id)
        if not loc:
            raise NotFoundException(detail="Location not found")

        return location_service.to_schema(loc, schema_type=Location)

    @patch("/{location_id:uuid}", status_code=HTTP_200_OK, summary="Update location")
    async def update_location(
        self,
        location_service: LocationService,
        location_id: UUID,
        data: LocationUpdate,
    ) -> Location:
        """Update an existing location."""
        loc = await location_service.update(
            data.model_dump(exclude_unset=True), location_id
        )
        if not loc:
            raise NotFoundException(detail="Location not found")
        return location_service.to_schema(loc, schema_type=Location)

    @get(
        "/{location_id:uuid}/sessions",
        status_code=HTTP_200_OK,
        summary="Get location sessions",
    )
    async def get_location_sessions(
        self,
        location_id: UUID,
        location_service: LocationService,
        session_service: SessionService,
        include_archived: bool = False,
    ) -> service.OffsetPagination[Session]:
        """Get all sessions for a specific location."""
        # Verify location exists
        loc = await location_service.get(location_id)
        if not loc:
            raise NotFoundException(detail="Location not found")

        # Get sessions for this location
        filters = [m.Session.location_id == location_id]
        if not include_archived:
            filters.append(~m.Session.archived)

        results, total = await session_service.list_and_count(*filters)
        return session_service.to_schema(results, total, schema_type=Session)
