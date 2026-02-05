from __future__ import annotations
import logging

from litestar import Controller, get, patch
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK
from app.domains.caregiver.schemas.caregiver import CaregiverMe, CaregiverUpdate
from app.db import models as m
from app.domains.caregiver.services.caregiver import CaregiverService
from app.domains.caregiver.services.auth import AuthSessionService
from app.domains.caregiver.guards import get_current_caregiver
from advanced_alchemy.extensions.litestar import providers
from app.lib.deps import get_task_queue

logger = logging.getLogger(__name__)


class CaregiverController(Controller):
    """Authenticated caregiver endpoints (profile, students, signups)."""

    path = "/api/v1"
    tags = ["Caregiver"]
    dependencies = providers.create_service_dependencies(
        CaregiverService,
        "caregiver_service",
    )
    dependencies.update(
        providers.create_service_dependencies(
            AuthSessionService,
            "auth_session_service",
        )
    )
    dependencies.update(
        {
            "current_caregiver": Provide(get_current_caregiver),
        }
    )

    @get("/me", status_code=HTTP_200_OK, summary="Get current caregiver")
    async def me(
        self, caregiver_service: CaregiverService, current_caregiver: m.Caregiver
    ) -> CaregiverMe:
        """Return the currently authenticated caregiver profile."""
        return caregiver_service.to_schema(current_caregiver, schema_type=CaregiverMe)

    @patch("/me", status_code=HTTP_200_OK, summary="Update caregiver profile")
    async def update_me(
        self,
        caregiver_service: CaregiverService,
        current_caregiver: m.Caregiver,
        data: CaregiverUpdate,
    ) -> CaregiverMe:
        """Update caregiver name and phone number."""
        updated_caregiver = await caregiver_service.update(
            data.model_dump(exclude_unset=True), current_caregiver.id
        )

        if data.subscribe_newsletter:
            queue = await get_task_queue()
            await queue.enqueue(
                "notify_newsletter_subscription_task",
                email=updated_caregiver.email,
                name=updated_caregiver.name,
            )

        return caregiver_service.to_schema(updated_caregiver, schema_type=CaregiverMe)
