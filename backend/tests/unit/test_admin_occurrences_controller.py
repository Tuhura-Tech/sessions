from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from litestar.exceptions import NotFoundException
from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError

from app.domains.admin.controllers.occurrences import OccurrenceController
from app.domains.admin.schemas.occurrence import (
    OccurrenceCancellation,
    OccurrenceCreate,
    OccurrenceUpdate,
)


@dataclass
class FakeSession:
    id: UUID
    name: str


@dataclass
class FakeOccurrence:
    id: UUID
    session: FakeSession
    starts_at: datetime
    cancelled: bool = False
    cancellation_reason: str | None = None


class DummyQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def enqueue(self, task_name: str, **kwargs):  # noqa: ANN001
        self.calls.append((task_name, kwargs))


class DummyOccurrenceService:
    def __init__(self, occurrence: FakeOccurrence | None = None) -> None:
        self._occurrence = occurrence
        self.created: list[OccurrenceCreate] = []
        self.updated: list[dict] = []

    async def get(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        if self._occurrence is None:
            raise AlchemyNotFoundError("Occurrence not found")
        return self._occurrence

    async def create(self, data: OccurrenceCreate):
        self.created.append(data)
        return self._occurrence or data

    async def update(self, data: dict, _occurrence_id: UUID):
        if self._occurrence is None:
            raise AlchemyNotFoundError("Occurrence not found")
        self.updated.append(data)
        for key, value in data.items():
            setattr(self._occurrence, key, value)
        return self._occurrence

    def to_schema(self, data, **_):  # noqa: ANN001
        return data


def make_controller() -> OccurrenceController:
    return OccurrenceController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestAdminOccurrenceController:
    async def test_get_occurrence_not_found(self):
        controller = make_controller()
        service = DummyOccurrenceService(None)

        with pytest.raises(NotFoundException):
            await OccurrenceController.get_occurrence.fn(controller, uuid4(), service)

    async def test_update_occurrence_not_found(self):
        controller = make_controller()
        service = DummyOccurrenceService(None)
        data = OccurrenceUpdate(starts_at=datetime.now(tz=timezone.utc))

        with pytest.raises(NotFoundException):
            await OccurrenceController.update_occurrence.fn(
                controller, uuid4(), data, service
            )

    async def test_create_occurrence_returns_schema(self):
        controller = make_controller()
        occurrence_id = uuid4()
        session_id = uuid4()
        block_id = uuid4()
        starts_at = datetime.now(tz=timezone.utc)
        ends_at = starts_at + timedelta(hours=1)
        occurrence = FakeOccurrence(
            id=occurrence_id,
            session=FakeSession(id=session_id, name="Session"),
            starts_at=starts_at,
        )
        service = DummyOccurrenceService(occurrence)

        data = OccurrenceCreate(
            starts_at=starts_at,
            ends_at=ends_at,
            session_id=session_id,
            block_id=block_id,
        )

        result = await OccurrenceController.create_occurrence.fn(
            controller, data, service
        )

        assert result == occurrence
        assert service.created[-1] == data

    async def test_toggle_cancel_occurrence_not_found(self):
        controller = make_controller()
        service = DummyOccurrenceService(None)
        data = OccurrenceCancellation(cancelled=True, cancellation_reason="Bad weather")

        with pytest.raises(NotFoundException):
            await OccurrenceController.toggle_cancel_occurrence.fn(
                controller, uuid4(), data, service
            )

    async def test_toggle_cancel_occurrence_enqueues_notifications(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        occurrence_id = uuid4()
        session_id = uuid4()
        occurrence = FakeOccurrence(
            id=occurrence_id,
            session=FakeSession(id=session_id, name="Session"),
            starts_at=datetime.now(timezone.utc),
        )
        service = DummyOccurrenceService(occurrence)
        queue = DummyQueue()

        async def get_queue():
            return queue

        monkeypatch.setattr(
            "app.domains.admin.controllers.occurrences.get_task_queue",
            get_queue,
        )

        data = OccurrenceCancellation(cancelled=True, cancellation_reason="Bad weather")
        result = await OccurrenceController.toggle_cancel_occurrence.fn(
            controller,
            occurrence_id,
            data,
            service,
        )

        assert result.cancelled is True
        assert result.cancellation_reason == "Bad weather"
        assert queue.calls
        task_name, payload = queue.calls[0]
        assert task_name == "send_occurrence_cancelled_task"
        assert payload["occurrence_id"] == str(occurrence_id)
        assert payload["session_id"] == str(session_id)
        assert payload["session_name"] == "Session"
        assert payload["occurrence_date"] == occurrence.starts_at.isoformat()

    async def test_toggle_cancel_occurrence_reinstate_skips_queue(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        occurrence_id = uuid4()
        session_id = uuid4()
        occurrence = FakeOccurrence(
            id=occurrence_id,
            session=FakeSession(id=session_id, name="Session"),
            starts_at=datetime.now(timezone.utc),
            cancelled=True,
            cancellation_reason="Bad weather",
        )
        service = DummyOccurrenceService(occurrence)

        async def fail_queue():
            raise AssertionError("queue should not be requested")

        monkeypatch.setattr(
            "app.domains.admin.controllers.occurrences.get_task_queue",
            fail_queue,
        )

        data = OccurrenceCancellation(cancelled=False, cancellation_reason=None)
        result = await OccurrenceController.toggle_cancel_occurrence.fn(
            controller,
            occurrence_id,
            data,
            service,
        )

        assert result.cancelled is False
        assert result.cancellation_reason is None
