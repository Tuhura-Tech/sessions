"""
Unit tests for public sessions controller logic.
"""

from __future__ import annotations

from datetime import datetime, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from litestar.exceptions import NotFoundException, ValidationException

from app.domains.public.controllers.events import EventController
from app.domains.public.controllers.sessions import SessionController


class DummySessionService:
    def __init__(self, results=None, total=0):
        self.results = results or []
        self.total = total
        self.last_filters = []

    async def list_and_count(self, *args, **kwargs):
        self.last_filters = list(args)
        return self.results, self.total

    def to_schema(self, obj, schema_type):
        if schema_type.__name__ == "Session":
            return SimpleNamespace(blocks=[])
        return {
            "id": str(obj.id),
            "startsAt": obj.starts_at,
            "endsAt": obj.ends_at,
            "cancelled": obj.cancelled,
            "blockId": obj.block_id,
            "sessionId": obj.session_id,
            "cancellationReason": None,
        }


class DummyResult:
    def __init__(self, rows=None, session=None):
        self._rows = rows or []
        self._session = session

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._session


class DummySession:
    def __init__(self, session_id, archived=False):
        self.id = session_id
        self.name = "Session"
        self.year = 2026
        self.session_type = "term"
        self.age_lower = 5
        self.age_upper = 12
        self.day_of_week = 1
        self.start_time = time(9, 0)
        self.end_time = time(17, 0)
        self.description = None
        self.archived = archived
        self.location = SimpleNamespace(
            name="Location",
            address="Address",
            region="Region",
            lat=-41.0,
            lng=174.0,
        )
        self.blocks = [SimpleNamespace(name="Block 1")]
        block = SimpleNamespace(id=uuid4(), name="Block 1", block_type="term")
        self.block_links = [SimpleNamespace(block=block)]
        self.occurrences = [
            SimpleNamespace(
                id=uuid4(),
                block_id=block.id,
                starts_at=datetime(2026, 2, 1, 9, 0, 0),
                ends_at=datetime(2026, 2, 1, 10, 0, 0),
                cancelled=False,
                session_id=self.id,
            )
        ]


@pytest.mark.anyio
async def test_list_sessions_negative_limit():
    controller = SessionController.__new__(SessionController)

    with pytest.raises(ValidationException):
        await SessionController.list_sessions.fn(
            controller,
            sessions_service=DummySessionService(),
            db_session=SimpleNamespace(execute=lambda *_: None),
            limit=-1,
            offset=None,
        )


@pytest.mark.anyio
async def test_list_sessions_negative_offset():
    controller = SessionController.__new__(SessionController)

    with pytest.raises(ValidationException):
        await SessionController.list_sessions.fn(
            controller,
            sessions_service=DummySessionService(),
            db_session=SimpleNamespace(execute=lambda *_: None),
            limit=None,
            offset=-1,
        )


@pytest.mark.anyio
async def test_list_sessions_success():
    controller = SessionController.__new__(SessionController)
    session_id = uuid4()
    session = SimpleNamespace(
        id=session_id,
        name="Session",
        year=2026,
        session_type="term",
        age_lower=5,
        age_upper=12,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
        description=None,
        location=SimpleNamespace(
            name="Location",
            address="Address",
            region="Region",
            lat=-41.0,
            lng=174.0,
        ),
    )
    service = DummySessionService(results=[session], total=1)

    async def execute(_query):
        return DummyResult(rows=[(session_id, "Block A")])

    db_session = SimpleNamespace(execute=execute)

    result = await SessionController.list_sessions.fn(
        controller,
        sessions_service=service,
        db_session=db_session,
        limit=10,
        offset=0,
    )

    assert result.total == 1
    assert result.items[0].blocks == ["Block A"]


@pytest.mark.anyio
async def test_list_events_success():
    controller = EventController.__new__(EventController)
    session_id = uuid4()
    session = SimpleNamespace(
        id=session_id,
        name="Event",
        year=2026,
        session_type="event",
        age_lower=8,
        age_upper=12,
        day_of_week=None,
        start_time=time(10, 0),
        end_time=time(12, 0),
        description="One-off event",
        location=SimpleNamespace(
            name="Location",
            address="Address",
            region="Region",
            lat=-41.0,
            lng=174.0,
        ),
    )
    service = DummySessionService(results=[session], total=1)

    async def execute(_query):
        return DummyResult(rows=[(session_id, "Special")])

    db_session = SimpleNamespace(execute=execute)

    result = await EventController.list_events.fn(
        controller,
        sessions_service=service,
        db_session=db_session,
        limit=10,
        offset=0,
    )

    assert result.total == 1
    assert result.items[0].session_type == "event"
    assert result.items[0].blocks == ["Special"]


@pytest.mark.anyio
async def test_get_session_not_found():
    controller = SessionController.__new__(SessionController)

    async def execute(_query):
        return DummyResult(session=None)

    db_session = SimpleNamespace(execute=execute)
    service = DummySessionService()

    with pytest.raises(NotFoundException):
        await SessionController.get_session.fn(controller, service, uuid4(), db_session)


@pytest.mark.anyio
async def test_get_session_archived():
    controller = SessionController.__new__(SessionController)
    session = DummySession(uuid4(), archived=True)

    async def execute(_query):
        return DummyResult(session=session)

    db_session = SimpleNamespace(execute=execute)
    service = DummySessionService()

    with pytest.raises(NotFoundException):
        await SessionController.get_session.fn(
            controller, service, session.id, db_session
        )


@pytest.mark.anyio
async def test_get_session_success():
    controller = SessionController.__new__(SessionController)
    session = DummySession(uuid4(), archived=False)

    async def execute(_query):
        return DummyResult(session=session)

    db_session = SimpleNamespace(execute=execute)
    service = DummySessionService()

    result = await SessionController.get_session.fn(
        controller, service, session.id, db_session
    )
    assert result.id == session.id
    assert result.location.name == "Location"
    assert result.blocks == ["Block 1"]
    assert result.occurrences_by_block
