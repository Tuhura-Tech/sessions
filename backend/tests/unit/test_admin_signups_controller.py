from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from litestar.exceptions import NotFoundException

from app.domains.admin.controllers.signups import SignupController
from app.domains.admin.schemas.signup import (
    SignupStatus,
    SignupStatusUpdate,
    SignupUpdate,
)


@dataclass
class FakeCaregiver:
    name: str
    email: str


@dataclass
class FakeStudent:
    name: str
    caregiver: FakeCaregiver


@dataclass
class FakeLocation:
    name: str
    address: str | None = None


@dataclass
class FakeSession:
    name: str
    id: str = "session-123"
    venue: str | None = None
    address: str | None = None
    location: FakeLocation | None = None


@dataclass
class FakeSignup:
    id: str
    status: SignupStatus
    student: FakeStudent
    session: FakeSession
    withdrawn_at: datetime | None = None


class DummyQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def enqueue(self, task_name: str, **kwargs):
        self.calls.append((task_name, kwargs))


class DummySignupService:
    def __init__(self, signup=None):
        self._signup = signup
        self.updated: list[dict] = []

    async def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self._signup

    async def create(self, data):  # noqa: ANN001
        return data

    async def update(self, data, _signup_id):  # noqa: ANN001
        self.updated.append(data)
        if self._signup is None:
            return None
        for key, value in data.items():
            setattr(self._signup, key, value)
        return self._signup

    def to_schema(self, data, **_):  # noqa: ANN001
        return data


def make_controller() -> SignupController:
    return SignupController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestAdminSignupController:
    async def test_get_signup_not_found(self):
        controller = make_controller()
        service = DummySignupService(signup=None)

        with pytest.raises(NotFoundException):
            await SignupController.get_signup.fn(controller, uuid4(), service)

    async def test_update_signup_sets_withdrawn_at(self):
        controller = make_controller()
        signup = FakeSignup(
            id="1",
            status=SignupStatus.CONFIRMED,
            student=FakeStudent(
                name="Student",
                caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
            ),
            session=FakeSession(name="Session"),
        )
        service = DummySignupService(signup)

        data = SignupUpdate(status=SignupStatus.WITHDRAWN)
        result = await SignupController.update_signup.fn(
            controller, uuid4(), data, service
        )

        assert result.withdrawn_at is not None
        assert service.updated[-1]["status"] == SignupStatus.WITHDRAWN

    async def test_update_signup_status_notify_confirmed(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        queue = DummyQueue()

        async def get_queue():
            return queue

        monkeypatch.setattr(
            "app.domains.admin.controllers.signups.get_task_queue",
            get_queue,
        )

        signup = FakeSignup(
            id="1",
            status=SignupStatus.WAITLISTED,
            student=FakeStudent(
                name="Student",
                caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
            ),
            session=FakeSession(name="Session", venue="Venue", address="Addr"),
        )
        service = DummySignupService(signup)

        data = SignupStatusUpdate(
            status=SignupStatus.CONFIRMED,
            notify_caregiver=True,
        )
        await SignupController.update_signup_status.fn(
            controller, uuid4(), data, service
        )

        assert queue.calls
        assert queue.calls[0][0] == "send_waitlist_promoted_task"

    async def test_update_signup_status_notify_withdrawn(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        queue = DummyQueue()

        async def get_queue():
            return queue

        monkeypatch.setattr(
            "app.domains.admin.controllers.signups.get_task_queue",
            get_queue,
        )

        signup = FakeSignup(
            id="1",
            status=SignupStatus.CONFIRMED,
            student=FakeStudent(
                name="Student",
                caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
            ),
            session=FakeSession(name="Session"),
        )
        service = DummySignupService(signup)

        data = SignupStatusUpdate(
            status=SignupStatus.WITHDRAWN,
            notify_caregiver=True,
            reason="No show",
        )
        await SignupController.update_signup_status.fn(
            controller, uuid4(), data, service
        )

        assert queue.calls
        assert queue.calls[0][0] == "send_signup_cancelled_task"
        assert queue.calls[0][1]["cancellation_reason"] == "No show"

    async def test_update_signup_status_demote_to_waitlist(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        queue = DummyQueue()

        async def get_queue():
            return queue

        monkeypatch.setattr(
            "app.domains.admin.controllers.signups.get_task_queue",
            get_queue,
        )

        signup = FakeSignup(
            id="1",
            status=SignupStatus.CONFIRMED,
            student=FakeStudent(
                name="Student",
                caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
            ),
            session=FakeSession(name="Session", venue="Venue", address="Addr"),
        )
        service = DummySignupService(signup)

        data = SignupStatusUpdate(
            status=SignupStatus.WAITLISTED,
            notify_caregiver=True,
        )
        await SignupController.update_signup_status.fn(
            controller, uuid4(), data, service
        )

        assert queue.calls
        assert queue.calls[0][0] == "send_signup_confirmation_task"
        assert queue.calls[0][1]["signup_status"] == "waitlisted"

    async def test_update_signup_status_clears_withdrawn_at(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()

        async def get_queue():
            return DummyQueue()

        monkeypatch.setattr(
            "app.domains.admin.controllers.signups.get_task_queue",
            get_queue,
        )

        signup = FakeSignup(
            id="1",
            status=SignupStatus.WITHDRAWN,
            withdrawn_at=datetime.now(timezone.utc),
            student=FakeStudent(
                name="Student",
                caregiver=FakeCaregiver(name="Caregiver", email="c@example.com"),
            ),
            session=FakeSession(name="Session"),
        )
        service = DummySignupService(signup)

        data = SignupStatusUpdate(status=SignupStatus.CONFIRMED)
        await SignupController.update_signup_status.fn(
            controller, uuid4(), data, service
        )

        assert service.updated[-1]["withdrawn_at"] is None
