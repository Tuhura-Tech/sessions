"""
Unit tests for caregiver profile controller logic.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.caregiver.controllers.caregiver import CaregiverController
from app.domains.caregiver.schemas.caregiver import CaregiverUpdate


class DummyCaregiverService:
    def __init__(self, updated=None):
        self.updated = updated
        self.update_calls = []

    async def update(self, data, caregiver_id):
        self.update_calls.append((caregiver_id, data))
        return self.updated

    def to_schema(self, caregiver, schema_type):
        return {
            "id": str(caregiver.id),
            "email": caregiver.email,
            "name": caregiver.name,
            "phone": caregiver.phone,
        }


@pytest.mark.anyio
async def test_me_returns_schema():
    controller = CaregiverController.__new__(CaregiverController)
    caregiver = SimpleNamespace(id=uuid4(), email="a@b.com", name="Name", phone="123")
    service = DummyCaregiverService(updated=caregiver)

    result = await CaregiverController.me.fn(controller, service, caregiver)
    assert result["email"] == "a@b.com"


@pytest.mark.anyio
async def test_update_me_subscribe_newsletter(monkeypatch):
    controller = CaregiverController.__new__(CaregiverController)
    caregiver = SimpleNamespace(id=uuid4(), email="a@b.com", name="Name", phone="123")
    updated = SimpleNamespace(
        id=caregiver.id, email="a@b.com", name="Updated", phone="456"
    )
    service = DummyCaregiverService(updated=updated)

    class DummyQueue:
        async def enqueue(self, *args, **kwargs):
            return None

    async def fake_get_task_queue():
        return DummyQueue()

    monkeypatch.setattr(
        "app.domains.caregiver.controllers.caregiver.get_task_queue",
        fake_get_task_queue,
    )

    data = CaregiverUpdate(name="Updated", phone="456", subscribe_newsletter=True)
    result = await CaregiverController.update_me.fn(
        controller, service, caregiver, data
    )

    assert result["name"] == "Updated"
    assert service.update_calls
