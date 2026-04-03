from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from litestar.exceptions import NotFoundException

from app.db import models as m
from app.domains.admin.controllers.sessions import SessionController
from app.domains.admin.schemas.session import SessionCreate, SessionUpdate


@dataclass
class FakeBlock:
    id: UUID
    start_date: date
    end_date: date


@dataclass
class FakeExclusion:
    date: date


@dataclass
class FakeCaregiver:
    name: str
    email: str
    phone: str | None = None


@dataclass
class FakeStudent:
    id: UUID
    name: str
    date_of_birth: date
    caregiver: FakeCaregiver
    media_consent: bool = True
    medical_info: str | None = None


@dataclass
class FakeSignup:
    id: UUID
    student: FakeStudent
    status: str
    needs_devices: bool
    pickup_dropoff: str | None
    created_at: datetime


@dataclass
class FakeOccurrence:
    id: UUID
    session_id: UUID
    starts_at: datetime
    ends_at: datetime


@dataclass
class FakeAttendance:
    status: str
    reason: str | None
    created_at: datetime


class DummyListService:
    def __init__(self, items):
        self._items = items

    async def list(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._items)

    def to_schema(self, items, *args, **kwargs):  # noqa: ANN001
        return items


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class DummyRepository:
    class DummySession:
        def __init__(self, rows):
            self._rows = rows

        async def execute(self, _stmt):  # noqa: ANN001
            return DummyResult(self._rows)

    def __init__(self, rows):
        self.session = self.DummySession(rows)


class DummySessionService:
    def __init__(self, session=None, list_results=None, attendance_rows=None):
        self._session = session
        self._list_results = list_results or []
        self._occurrences = []
        self._signups = []
        self.created_links: list[m.BlockLink] = []
        self.created_occurrences: list[m.Occurrence] = []
        self.updated_payloads: list[dict] = []
        self.repository = DummyRepository(attendance_rows or [])

        self.blocks = SimpleNamespace(get=self._get_block)
        self.exclusions = SimpleNamespace(list=self._list_exclusions)
        self.occurrences = SimpleNamespace(
            create=self._create_occurrence,
            list=self._list_occurrences,
            to_schema=lambda items, **_: items,
        )
        self.signups = SimpleNamespace(
            list=self._list_signups,
            to_schema=lambda items, **_: items,
        )
        self.session_block_service = SimpleNamespace(create=self._create_block_link)

        self._blocks: dict[UUID, FakeBlock] = {}
        self._exclusions: list[FakeExclusion] = []

    def to_schema(self, data, total=None, **_):  # noqa: ANN001
        if total is not None:
            return {"items": data, "total": total}
        return data

    async def list_and_count(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._list_results), len(self._list_results)

    async def get(self, _id, *args, **kwargs):  # noqa: ANN002, ANN003
        return self._session

    async def create(self, data):  # noqa: ANN001
        session = SimpleNamespace(
            id=uuid4(),
            year=data.year,
            day_of_week=data.day_of_week,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        session.session_type = getattr(data, "session_type", "term")
        self._session = session
        return session

    async def update(self, data, _id):  # noqa: ANN001
        self.updated_payloads.append(data)
        return self._session

    async def _create_block_link(self, link):
        self.created_links.append(link)
        return link

    async def _get_block(self, block_id):
        return self._blocks[block_id]

    async def _list_exclusions(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._exclusions)

    async def _create_occurrence(self, occurrence):
        self.created_occurrences.append(occurrence)
        return occurrence

    async def _list_occurrences(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._occurrences)

    async def _list_signups(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._signups)


def make_controller() -> SessionController:
    return SessionController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestAdminSessionController:
    async def test_list_sessions(self):
        controller = make_controller()
        session_service = DummySessionService(list_results=["one", "two"])

        result = await SessionController.list_sessions.fn(controller, session_service)

        assert result == {"items": ["one", "two"], "total": 2}

    async def test_get_session_not_found(self):
        controller = make_controller()
        session_service = DummySessionService(session=None)

        with pytest.raises(NotFoundException):
            await SessionController.get_session.fn(controller, uuid4(), session_service)

    async def test_create_session_creates_occurrences(self):
        controller = make_controller()
        block_id = uuid4()
        block = FakeBlock(
            id=block_id,
            start_date=date(2026, 2, 2),
            end_date=date(2026, 2, 16),
        )
        exclusions = [FakeExclusion(date=date(2026, 2, 9))]

        session_service = DummySessionService()
        session_service._blocks[block_id] = block
        session_service._exclusions = exclusions

        data = SessionCreate(
            year=2026,
            session_type="term",
            name="Test Session",
            age_lower=8,
            age_upper=12,
            start_time=time(9, 0),
            end_time=time(10, 0),
            day_of_week=0,
            capacity=20,
            location_id=uuid4(),
            blocks=[block_id],
        )

        created = await SessionController.create_session.fn(
            controller,
            data=data,
            session_service=session_service,
        )

        assert created is session_service._session
        assert len(session_service.created_links) == 1
        assert len(session_service.created_occurrences) == 2

    async def test_update_session_not_found(self):
        controller = make_controller()
        session_service = DummySessionService(session=None)
        data = SessionUpdate(name="Updated")

        with pytest.raises(NotFoundException):
            await SessionController.update_session.fn(
                controller, uuid4(), data, session_service
            )

    async def test_get_occurrences(self):
        controller = make_controller()
        session_id = uuid4()
        session = SimpleNamespace(id=session_id)
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=datetime(2026, 2, 2, 9, 0),
            ends_at=datetime(2026, 2, 2, 10, 0),
        )
        session_service = DummySessionService(session=session)
        session_service._occurrences = [occurrence]

        result = await SessionController.get_occurrences.fn(
            controller, session_id, session_service
        )

        assert result == [occurrence]

    async def test_get_signups(self):
        controller = make_controller()
        session_id = uuid4()
        session = SimpleNamespace(id=session_id)
        student = FakeStudent(
            id=uuid4(),
            name="Student",
            date_of_birth=date(2016, 1, 1),
            caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
        )
        signup = FakeSignup(
            id=uuid4(),
            student=student,
            status="confirmed",
            needs_devices=False,
            pickup_dropoff=None,
            created_at=datetime(2026, 2, 1, 9, 0),
        )
        session_service = DummySessionService(session=session)
        session_service._signups = [signup]

        result = await SessionController.get_signups.fn(
            controller, session_id, session_service
        )

        assert result == [signup]

    async def test_export_signups_csv(self):
        controller = make_controller()
        session_id = uuid4()
        session = SimpleNamespace(id=session_id)
        caregiver = FakeCaregiver(name="Caregiver", email="c@example.com")
        student = FakeStudent(
            id=uuid4(),
            name="Student",
            date_of_birth=date(2016, 1, 1),
            caregiver=caregiver,
            media_consent=True,
        )
        signup = FakeSignup(
            id=uuid4(),
            student=student,
            status="confirmed",
            needs_devices=True,
            pickup_dropoff="Pickup",
            created_at=datetime(2026, 2, 1, 9, 0),
        )
        session_service = DummySessionService(session=session)
        session_service._signups = [signup]

        stream = await SessionController.export_signups_csv.fn(
            controller, session_id, session_service
        )

        output = "".join([chunk async for chunk in stream.iterator])
        assert "Signup ID" in output
        assert "Student" in output

    async def test_export_attendance_csv(self):
        controller = make_controller()
        session_id = uuid4()
        session = SimpleNamespace(id=session_id)
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=datetime(2026, 2, 2, 9, 0),
            ends_at=datetime(2026, 2, 2, 10, 0),
        )
        student = FakeStudent(
            id=uuid4(),
            name="Student",
            date_of_birth=date(2016, 1, 1),
            caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
        )
        attendance = FakeAttendance(
            status="present",
            reason=None,
            created_at=datetime(2026, 2, 2, 10, 0),
        )

        rows = [(attendance, occurrence, student)]
        session_service = DummySessionService(session=session, attendance_rows=rows)

        stream = await SessionController.export_attendance_csv.fn(
            controller, session_id, session_service
        )
        output = "".join([chunk async for chunk in stream.iterator])
        assert "Occurrence ID" in output
        assert "Student" in output

    async def test_email_session(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        controller = make_controller()
        session_id = uuid4()
        session_service = DummySessionService(session=SimpleNamespace(id=session_id))

        # Mock the get_task_queue function at the import location
        mock_queue = AsyncMock()
        mock_queue.enqueue = AsyncMock()

        async def mock_get_task_queue():
            return mock_queue

        monkeypatch.setattr("app.lib.deps.get_task_queue", mock_get_task_queue)

        # Mock the database query for counting confirmed signups
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5

        async def mock_execute(_stmt):
            return mock_result

        # Set up the signups.repository.session with the mock execute
        mock_session = MagicMock()
        mock_session.execute = mock_execute

        mock_repository = MagicMock()
        mock_repository.session = mock_session

        session_service.signups.repository = mock_repository

        result = await SessionController.email_session.fn(
            controller,
            session_id,
            session_service,
            data=SimpleNamespace(subject="Test", message="Test message"),
        )

        # Verify the result contains enqueued count
        assert result == {"enqueued": 5}

        # Verify that the task was enqueued
        mock_queue.enqueue.assert_awaited_once()
