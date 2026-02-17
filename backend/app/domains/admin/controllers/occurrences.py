from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError
from advanced_alchemy.extensions.litestar import providers
from litestar import Controller, get, patch, post
from litestar.exceptions import NotFoundException
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.occurrence import (
    Occurrence,
    OccurrenceCreate,
    OccurrenceUpdate,
)
from app.domains.admin.services.occurrences import OccurrenceService
from app.lib.deps import get_task_queue

logger = logging.getLogger(__name__)


class OccurrenceController(Controller):
    """Admin endpoints for managing sessions."""

    path = "/api/v1/admin/occurrences"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        OccurrenceService,
        "occurrence_service",
    )

    @get("/{occurrence_id:uuid}")
    async def get_occurrence(
        self,
        occurrence_id: UUID,
        occurrence_service: OccurrenceService,
    ) -> Occurrence:
        """Get a single occurrence by ID."""
        try:
            occurrence = await occurrence_service.get(occurrence_id)
        except AlchemyNotFoundError as exc:
            raise NotFoundException(detail="Occurrence not found") from exc
        return occurrence_service.to_schema(occurrence, schema_type=Occurrence)

    @patch("/{occurrence_id:uuid}")
    async def update_occurrence(
        self,
        occurrence_id: UUID,
        data: OccurrenceUpdate,
        occurrence_service: OccurrenceService,
    ) -> Occurrence:
        """Update an existing occurrence."""
        try:
            occurrence = await occurrence_service.update(
                data.model_dump(exclude_unset=True), occurrence_id
            )
        except AlchemyNotFoundError as exc:
            raise NotFoundException(detail="Occurrence not found") from exc
        return occurrence_service.to_schema(occurrence, schema_type=Occurrence)

    @post("/")
    async def create_occurrence(
        self,
        data: OccurrenceCreate,
        occurrence_service: OccurrenceService,
    ) -> Occurrence:
        """Create a new occurrence."""
        occurrence = await occurrence_service.create(data)
        return occurrence_service.to_schema(occurrence, schema_type=Occurrence)

    @patch("/{occurrence_id:uuid}/cancel")
    async def toggle_cancel_occurrence(
        self,
        occurrence_id: UUID,
        occurrence_service: OccurrenceService,
        cancelled: bool = False,
        cancellation_reason: str | None = None,
    ) -> Occurrence:
        """Cancel or reinstate an occurrence.

        This endpoint allows admins to cancel an occurrence (e.g., due to bad weather,
        staff unavailability, etc.) or reinstate a previously cancelled occurrence.

        When an occurrence is cancelled, all confirmed signups are notified.

        Args:
            occurrence_id: The UUID of the occurrence to update
            occurrence_service: Injected occurrence service
            cancelled: True to cancel, False to reinstate
            cancellation_reason: Optional reason for cancellation (only used if cancelled=True)
        """
        # Get the occurrence with session loaded
        try:
            occurrence = await occurrence_service.get(
                occurrence_id,
                load=[selectinload(m.Occurrence.session)],
            )
        except AlchemyNotFoundError as exc:
            raise NotFoundException(detail="Occurrence not found") from exc

        occurrence_data = {
            "cancelled": cancelled,
            "cancellation_reason": cancellation_reason,
        }

        occurrence = await occurrence_service.update(occurrence_data, occurrence_id)

        # Queue notification emails if cancelling
        if cancelled:
            try:
                queue = await get_task_queue()
                await queue.enqueue(
                    "send_occurrence_cancelled_task",
                    occurrence_id=str(occurrence_id),
                    session_id=str(occurrence.session.id),
                    session_name=occurrence.session.name,
                    occurrence_date=occurrence.starts_at.isoformat(),
                    cancellation_reason=cancellation_reason,
                )
                logger.info(
                    f"Queued occurrence cancellation emails for occurrence {occurrence_id}"
                )
            except Exception as e:
                logger.error(f"Failed to queue occurrence cancellation emails: {e}")

        return occurrence_service.to_schema(occurrence, schema_type=Occurrence)
