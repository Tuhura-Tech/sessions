"""
Unit tests for public health controller logic.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domains.public.controllers.health import HealthController


class FailingSession:
    async def execute(self, _query):
        raise SQLAlchemyError("db down")


@pytest.mark.anyio
async def test_health_check_offline():
    controller = HealthController.__new__(HealthController)
    result = await HealthController.health_check.fn(controller, FailingSession())
    assert result.status is False
