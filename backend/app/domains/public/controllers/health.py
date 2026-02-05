"""Health check endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from litestar import Controller, get

from app.lib.settings import settings
from sqlalchemy.exc import SQLAlchemyError

from typing import TYPE_CHECKING, Literal
from sqlalchemy import text

from app.domains.public.schemas.health import (
    HealthCheckResponse,
    ReadinessCheckResponse,
    LivenessCheckResponse,
)


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class HealthController(Controller):
    """Health check endpoints."""

    path = ""
    tags = ["Public"]

    @get("/api/v1/health", summary="Health check")
    async def health_check(
        self,
        db_session: AsyncSession,
    ) -> HealthCheckResponse:
        """Health check endpoint with telemetry and version information.

        Returns:
            Health status including service version and telemetry info
        """

        db_status: Literal["online", "offline"]
        try:
            await db_session.execute(text("select 1"))
            db_status = "online"
        except SQLAlchemyError:
            db_status = "offline"

        return HealthCheckResponse(
            status=db_status == "online",
            timestamp=datetime.now(UTC).isoformat(),
            version="1.0.0",
            service="tuhura-sessions-api",
            debug=settings.debug,
        )

    @get("/api/v1/health/ready", summary="Readiness check")
    async def readiness_check(self) -> ReadinessCheckResponse:
        """Readiness check for Kubernetes/orchestrators.

        Returns:
            Readiness status
        """
        return ReadinessCheckResponse(
            ready=True,
            timestamp=datetime.now(UTC).isoformat(),
        )

    @get("/api/v1/health/live", summary="Liveness check")
    async def liveness_check(self) -> LivenessCheckResponse:
        """Liveness check for Kubernetes/orchestrators.

        Returns:
            Liveness status
        """
        return LivenessCheckResponse(
            alive=True,
            timestamp=datetime.now(UTC).isoformat(),
        )
