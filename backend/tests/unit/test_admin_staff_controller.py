from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from litestar.exceptions import NotFoundException, ValidationException
from sqlalchemy.exc import IntegrityError

from app.domains.admin.controllers.staff import SessionStaffController, StaffController
from app.domains.admin.schemas.staff import (
    BulkStaffAssignment,
    StaffCreate,
    StaffUpdate,
)


@dataclass
class FakeStaff:
    id: UUID
    name: str
    email: str
    sso_id: str
    active: bool
    last_login_at: datetime | None = None
    deactivated_at: datetime | None = None


@dataclass
class FakeLocation:
    id: UUID
    name: str
    address: str
    region: str
    lat: float
    lng: float
    contact_name: str
    contact_email: str


@dataclass
class FakeSession:
    id: UUID
    name: str
    year: int
    session_type: str
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    location_name: str | None = None
    location: FakeLocation | None = None


@dataclass
class FakeAssignment:
    id: UUID
    staff_id: UUID
    session_id: UUID
    assigned_at: datetime
    staff: FakeStaff | None = None
    session: FakeSession | None = None


@dataclass
class FakeOccurrence:
    starts_at: datetime


class DummyStaffService:
    def __init__(self, staff: FakeStaff | None = None, list_results=None):
        self._staff = staff
        self._list_results = list_results or []
        self.list_filters: list[dict] = []
        self.created: list[dict] = []
        self.updated: list[dict] = []

    async def list(self, **filters):
        self.list_filters.append(filters)
        return list(self._list_results)

    async def get(self, _id):  # noqa: ANN001
        return self._staff

    async def create(self, data: dict):
        self.created.append(data)
        self._staff = FakeStaff(
            id=uuid4(),
            name=data["name"],
            email=data["email"],
            sso_id=data["sso_id"],
            active=data["active"],
        )
        return self._staff

    async def update(self, data: dict, _id):  # noqa: ANN001
        self.updated.append(data)
        if not self._staff:
            return None
        for key, value in data.items():
            setattr(self._staff, key, value)
        return self._staff

    def to_schema(self, staff, **_):  # noqa: ANN001
        return staff


class DummySessionStaffService:
    def __init__(self, assignments=None):
        self._assignments = assignments or []
        self.created: list[dict] = []
        self.deleted: list[UUID] = []
        self.create_error: str | None = None

    async def list(self, **filters):
        staff_id = filters.get("staff_id")
        session_id = filters.get("session_id")
        if staff_id is not None:
            return [a for a in self._assignments if a.staff_id == staff_id]
        if session_id is not None:
            return [a for a in self._assignments if a.session_id == session_id]
        return list(self._assignments)

    async def create(self, data: dict):
        if self.create_error:
            raise IntegrityError(self.create_error, None, None)
        assignment = FakeAssignment(
            id=uuid4(),
            staff_id=data["staff_id"],
            session_id=data["session_id"],
            assigned_at=datetime.now(timezone.utc),
        )
        self.created.append(data)
        self._assignments.append(assignment)
        return assignment

    async def delete(self, assignment_id: UUID):
        self.deleted.append(assignment_id)


class DummySessionService:
    def __init__(self, occurrences=None):
        self.occurrences = SimpleNamespace(list=self._list_occurrences)
        self._occurrences = occurrences or []

    async def _list_occurrences(self, **_):
        return list(self._occurrences)


def make_staff_controller() -> StaffController:
    return StaffController(owner=SimpleNamespace())


def make_session_staff_controller() -> SessionStaffController:
    return SessionStaffController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestStaffController:
    async def test_list_staff_active_only(self):
        controller = make_staff_controller()
        staff_service = DummyStaffService(list_results=[])

        await StaffController.list_staff.fn(controller, staff_service, active_only=True)
        assert staff_service.list_filters[-1] == {"active": True}

    async def test_get_staff_not_found(self):
        controller = make_staff_controller()
        staff_service = DummyStaffService(staff=None)

        with pytest.raises(NotFoundException):
            await StaffController.get_staff.fn(controller, uuid4(), staff_service)

    async def test_create_staff_validation(self):
        controller = make_staff_controller()
        existing = FakeStaff(
            id=uuid4(),
            name="Existing",
            email="e@example.com",
            sso_id="sso",
            active=True,
        )
        staff_service = DummyStaffService(list_results=[existing])

        data = StaffCreate(name="New", email="e@example.com", sso_id="sso")
        with pytest.raises(ValidationException):
            await StaffController.create_staff.fn(controller, data, staff_service)

    async def test_create_staff_success(self):
        controller = make_staff_controller()
        staff_service = DummyStaffService(list_results=[])

        data = StaffCreate(name="New", email="n@example.com", sso_id="sso-new")
        staff = await StaffController.create_staff.fn(controller, data, staff_service)

        assert staff.email == "n@example.com"

    async def test_update_staff_deactivate_removes_future_sessions(self):
        controller = make_staff_controller()
        staff = FakeStaff(
            id=uuid4(),
            name="Staff",
            email="s@example.com",
            sso_id="sso",
            active=True,
        )
        staff_service = DummyStaffService(staff=staff)
        assignment = FakeAssignment(
            id=uuid4(),
            staff_id=staff.id,
            session_id=uuid4(),
            assigned_at=datetime.now(timezone.utc),
        )
        session_staff_service = DummySessionStaffService([assignment])
        future_occurrence = FakeOccurrence(
            starts_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        session_service = DummySessionService([future_occurrence])

        data = StaffUpdate(active=False)
        updated = await StaffController.update_staff.fn(
            controller,
            staff.id,
            data,
            staff_service,
            session_staff_service,
            session_service,
        )

        assert updated.active is False
        assert session_staff_service.deleted == [assignment.id]

    async def test_update_staff_reactivate(self):
        controller = make_staff_controller()
        staff = FakeStaff(
            id=uuid4(),
            name="Staff",
            email="s@example.com",
            sso_id="sso",
            active=False,
            deactivated_at=datetime.now(timezone.utc),
        )
        staff_service = DummyStaffService(staff=staff)
        session_staff_service = DummySessionStaffService([])
        session_service = DummySessionService([])

        data = StaffUpdate(active=True)
        updated = await StaffController.update_staff.fn(
            controller,
            staff.id,
            data,
            staff_service,
            session_staff_service,
            session_service,
        )

        assert updated.deactivated_at is None

    async def test_get_staff_sessions(self):
        controller = make_staff_controller()
        staff = FakeStaff(
            id=uuid4(),
            name="Staff",
            email="s@example.com",
            sso_id="sso",
            active=True,
        )
        session = FakeSession(
            id=uuid4(), name="Session", year=2026, session_type="term"
        )
        assignment = FakeAssignment(
            id=uuid4(),
            staff_id=staff.id,
            session_id=session.id,
            assigned_at=datetime.now(timezone.utc),
            session=session,
        )
        staff_service = DummyStaffService(staff=staff)
        session_staff_service = DummySessionStaffService([assignment])

        results = await StaffController.get_staff_sessions.fn(
            controller, staff.id, staff_service, session_staff_service
        )

        assert results[0].name == "Session"

    async def test_get_staff_availability_year_filter(self):
        controller = make_staff_controller()
        staff = FakeStaff(
            id=uuid4(),
            name="Staff",
            email="s@example.com",
            sso_id="sso",
            active=True,
        )
        session_a = FakeSession(id=uuid4(), name="A", year=2026, session_type="term")
        session_b = FakeSession(id=uuid4(), name="B", year=2025, session_type="term")
        assignments = [
            FakeAssignment(
                id=uuid4(),
                staff_id=staff.id,
                session_id=session_a.id,
                assigned_at=datetime.now(timezone.utc),
                session=session_a,
            ),
            FakeAssignment(
                id=uuid4(),
                staff_id=staff.id,
                session_id=session_b.id,
                assigned_at=datetime.now(timezone.utc),
                session=session_b,
            ),
        ]
        staff_service = DummyStaffService(staff=staff, list_results=[staff])
        session_staff_service = DummySessionStaffService(assignments)

        results = await StaffController.get_staff_availability.fn(
            controller,
            staff_service,
            session_staff_service,
            year=2026,
            active_only=True,
        )

        assert results[0].assigned_session_count == 1


@pytest.mark.anyio
class TestSessionStaffController:
    async def test_get_session_staff(self):
        controller = make_session_staff_controller()
        staff = FakeStaff(
            id=uuid4(),
            name="Staff",
            email="s@example.com",
            sso_id="sso",
            active=True,
        )
        assignment = FakeAssignment(
            id=uuid4(),
            staff_id=staff.id,
            session_id=uuid4(),
            assigned_at=datetime.now(timezone.utc),
            staff=staff,
        )
        session_staff_service = DummySessionStaffService([assignment])

        results = await SessionStaffController.get_session_staff.fn(
            controller, assignment.session_id, SimpleNamespace(), session_staff_service
        )

        assert results[0].email == "s@example.com"

    async def test_assign_staff_duplicate(self):
        from app.domains.admin.schemas.staff import StaffAssignmentCreate
        
        controller = make_session_staff_controller()
        session_staff_service = DummySessionStaffService([])
        session_staff_service.create_error = "uq_session_staff"
        staff_id = uuid4()
        data = StaffAssignmentCreate(staff_id=staff_id)

        with pytest.raises(ValidationException):
            await SessionStaffController.assign_staff.fn(
                controller,
                uuid4(),
                data,
                SimpleNamespace(),
                SimpleNamespace(),
                session_staff_service,
            )

    async def test_remove_staff_not_found(self):
        controller = make_session_staff_controller()
        session_staff_service = DummySessionStaffService([])

        with pytest.raises(NotFoundException):
            await SessionStaffController.remove_staff.fn(
                controller, uuid4(), uuid4(), session_staff_service
            )

    async def test_bulk_assign_staff_replace(self):
        controller = make_session_staff_controller()
        existing = FakeAssignment(
            id=uuid4(),
            staff_id=uuid4(),
            session_id=uuid4(),
            assigned_at=datetime.now(timezone.utc),
        )
        session_staff_service = DummySessionStaffService([existing])

        data = BulkStaffAssignment(staff_ids=[uuid4(), uuid4()], replace=True)
        results = await SessionStaffController.bulk_assign_staff.fn(
            controller, existing.session_id, data, session_staff_service
        )

        assert session_staff_service.deleted == [existing.id]
        assert len(results) == 2
