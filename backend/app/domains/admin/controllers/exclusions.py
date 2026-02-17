from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError
from advanced_alchemy.extensions.litestar import providers, service
from litestar import Controller, delete, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.domains.admin.schemas.exclusion import (
    ExclusionDate,
    ExclusionDateCreate,
    ExclusionDateUpdate,
)
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.services.exclusion import ExclusionService

logger = logging.getLogger(__name__)


class ExclusionController(Controller):
    """Public endpoints for caregivers (no auth required)."""

    path = "/api/v1/admin/exclusions"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        ExclusionService,
        "exclusion_service",
    )

    @get("/", status_code=HTTP_200_OK, summary="List exclusions")
    async def list_exclusions(
        self,
        exclusion_service: ExclusionService,
    ) -> service.OffsetPagination[ExclusionDate]:
        """List active public sessions sorted by region.

        Returns only non-archived sessions with their block associations.
        """
        results, total = await exclusion_service.list_and_count()
        return exclusion_service.to_schema(results, total, schema_type=ExclusionDate)

    @post("/")
    async def create_exclusion(
        self,
        exclusion_service: ExclusionService,
        data: ExclusionDateCreate,
    ) -> ExclusionDate:
        """Create a new exclusion date."""
        exclusion = await exclusion_service.create(data)
        return exclusion_service.to_schema(exclusion, schema_type=ExclusionDate)

    @get(
        "/{exclusion_id:uuid}",
        status_code=HTTP_200_OK,
        summary="Get exclusion date by ID",
    )
    async def get_exclusion(
        self,
        exclusion_service: ExclusionService,
        exclusion_id: UUID,
    ) -> ExclusionDate:
        """Get a specific exclusion date by ID."""
        try:
            exclusion = await exclusion_service.get(exclusion_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Exclusion date not found")
        if not exclusion:
            raise NotFoundException(detail="Exclusion date not found")

        return exclusion_service.to_schema(exclusion, schema_type=ExclusionDate)

    @patch(
        "/{exclusion_id:uuid}", status_code=HTTP_200_OK, summary="Update exclusion date"
    )
    async def update_exclusion(
        self,
        exclusion_service: ExclusionService,
        exclusion_id: UUID,
        data: ExclusionDateUpdate,
    ) -> ExclusionDate:
        """Update an existing exclusion date."""
        try:
            exclusion = await exclusion_service.update(
                data.model_dump(exclude_unset=True), exclusion_id
            )
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Exclusion date not found")
        if not exclusion:
            raise NotFoundException(detail="Exclusion date not found")
        return exclusion_service.to_schema(exclusion, schema_type=ExclusionDate)

    @delete(
        "/{exclusion_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        summary="Delete exclusion date",
    )
    async def delete_exclusion(
        self,
        exclusion_service: ExclusionService,
        exclusion_id: UUID,
    ) -> None:
        """Delete an exclusion date."""
        try:
            await exclusion_service.delete(exclusion_id)
        except AlchemyNotFoundError as exc:
            raise NotFoundException(detail="Exclusion date not found") from exc
