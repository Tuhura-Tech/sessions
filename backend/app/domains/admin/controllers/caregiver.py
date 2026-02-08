from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, delete, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.orm import joinedload, selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.caregiver import (
    Caregiver,
    CaregiverCreate,
    CaregiverMessage,
    CaregiverUpdate,
)
from app.domains.admin.schemas.student import Student
from app.domains.admin.services.caregiver import CaregiverService
from app.lib.deps import get_task_queue

logger = logging.getLogger(__name__)


class CaregiverController(Controller):
    """Admin endpoints for managing caregivers."""

    path = "/api/v1/admin/caregivers"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        CaregiverService,
        "caregiver_service",
        load=[
            selectinload(m.Caregiver.students).options(
                joinedload(m.Student.caregiver, innerjoin=True)
            )
        ],
    )

    @get("/")
    async def list_caregivers(
        self,
        caregiver_service: CaregiverService,
        limit: int = 100,
        offset: int = 0,
    ) -> service.OffsetPagination[Caregiver]:
        """List all caregivers with pagination.

        Args:
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)
        """
        results, total = await caregiver_service.list_and_count(
            LimitOffset(limit, offset)
        )
        return caregiver_service.to_schema(results, total, schema_type=Caregiver)

    @get("/{caregiver_id:uuid}")
    async def get_caregiver(
        self,
        caregiver_id: UUID,
        caregiver_service: CaregiverService,
    ) -> Caregiver:
        """Get a single caregiver by ID."""
        caregiver = await caregiver_service.get(caregiver_id)
        if not caregiver:
            raise NotFoundException(detail="Caregiver not found")
        return caregiver_service.to_schema(caregiver, schema_type=Caregiver)

    @post("/")
    async def create_caregiver(
        self,
        data: CaregiverCreate,
        caregiver_service: CaregiverService,
    ) -> Caregiver:
        """Create a new caregiver."""
        caregiver = await caregiver_service.create(data)
        if data.subscribe_newsletter:
            queue = await get_task_queue()
            await queue.enqueue(
                "notify_newsletter_subscription_task",
                email=data.email,
                name=data.name,
            )
        return caregiver_service.to_schema(caregiver, schema_type=Caregiver)

    @patch("/{caregiver_id:uuid}")
    async def update_caregiver(
        self,
        caregiver_id: UUID,
        data: CaregiverUpdate,
        caregiver_service: CaregiverService,
    ) -> Caregiver:
        """Update an existing caregiver."""
        caregiver = await caregiver_service.update(
            data.model_dump(exclude_unset=True), caregiver_id
        )
        if not caregiver:
            raise NotFoundException(detail="Caregiver not found")
        return caregiver_service.to_schema(caregiver, schema_type=Caregiver)

    @delete("/{caregiver_id:uuid}", status_code=HTTP_200_OK)
    async def delete_caregiver(
        self,
        caregiver_id: UUID,
        caregiver_service: CaregiverService,
    ) -> None:
        """Delete a caregiver."""
        deleted = await caregiver_service.delete(caregiver_id)
        if not deleted:
            raise NotFoundException(detail="Caregiver not found")

    @post("/{caregiver_id:uuid}/email")
    async def email_caregiver(
        self,
        caregiver_id: UUID,
        data: CaregiverMessage,
        caregiver_service: CaregiverService,
    ) -> dict:
        """Send an email message to a caregiver."""
        caregiver = await caregiver_service.get(caregiver_id)
        if not caregiver:
            raise NotFoundException(detail="Caregiver not found")

        queue = await get_task_queue()
        await queue.enqueue(
            "send_caregiver_message_task",
            to_email=caregiver.email,
            caregiver_name=caregiver.name or "Caregiver",
            subject=data.subject,
            message=data.message,
        )

        return {"ok": True}

    @get("/{caregiver_id:uuid}/students")
    async def list_caregiver_students(
        self,
        caregiver_id: UUID,
        caregiver_service: CaregiverService,
    ) -> service.OffsetPagination[Student]:
        """List all students associated with a caregiver."""
        caregiver = await caregiver_service.get(caregiver_id)
        if caregiver is None:
            raise NotFoundException(detail="Caregiver not found")
        return caregiver_service.to_schema(caregiver.students, schema_type=Student)
