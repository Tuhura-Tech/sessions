"""
Unit tests for caregiver signup controller logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from litestar.exceptions import NotFoundException, ValidationException

from app.domains.caregiver.controllers.signup import SignupController
from app.domains.caregiver.schemas.signup import SignupCreateRequest


class DummySignupService:
    def __init__(self, signups=None, create_result=None):
        self.signups = signups or []
        self.create_result = create_result
        self.updated = []
        self.created = []

    async def list(self, *args, **kwargs):
        return self.signups

    async def update(self, data, signup_id):
        self.updated.append((signup_id, data))
        return None

    async def create(self, data):
        self.created.append(data)
        return self.create_result

    async def get(self, signup_id, load=None):
        return None


class DummyStudentService:
    def __init__(self, student=None):
        self.student = student

    async def get(self, student_id):
        return self.student


class DummySessionService:
    def __init__(self, session=None):
        self.session = session

    async def get(self, session_id):
        return self.session


@pytest.mark.anyio
async def test_list_signups_builds_schema():
    controller = SignupController.__new__(SignupController)
    signup = SimpleNamespace(
        id=uuid4(),
        status="confirmed",
        created_at=datetime.now(timezone.utc),
        withdrawn_at=None,
        pickup_dropoff="parent",
        needs_devices=False,
        session_id=uuid4(),
        student_id=uuid4(),
        session=SimpleNamespace(name="Session A"),
        student=SimpleNamespace(name="Student A"),
    )
    signup_service = DummySignupService(signups=[signup])

    caregiver = SimpleNamespace(id=uuid4())
    results = await SignupController.list_signups.fn(
        controller,
        signup_service,
        caregiver,
    )

    assert len(results) == 1
    assert results[0].session_name == "Session A"
    assert results[0].student_name == "Student A"


@pytest.mark.anyio
async def test_create_signup_invalid_student_id():
    controller = SignupController.__new__(SignupController)
    session = SimpleNamespace(age_lower=5, age_upper=12)
    session_service = DummySessionService(session=session)
    student_service = DummyStudentService(student=None)
    signup_service = DummySignupService()

    caregiver = SimpleNamespace(id=uuid4(), name="Caregiver", phone="123")
    data = SignupCreateRequest(studentId="invalid")

    with pytest.raises(ValidationException):
        await SignupController.create_signup.fn(
            controller,
            uuid4(),
            data,
            signup_service,
            student_service,
            session_service,
            None,
            caregiver,
        )


@pytest.mark.anyio
async def test_create_signup_student_not_found():
    controller = SignupController.__new__(SignupController)
    session = SimpleNamespace(age_lower=5, age_upper=12)
    session_service = DummySessionService(session=session)
    student_service = DummyStudentService(student=None)
    signup_service = DummySignupService()

    caregiver = SimpleNamespace(id=uuid4(), name="Caregiver", phone="123")
    data = SignupCreateRequest(studentId=str(uuid4()))

    with pytest.raises(NotFoundException):
        await SignupController.create_signup.fn(
            controller,
            uuid4(),
            data,
            signup_service,
            student_service,
            session_service,
            None,
            caregiver,
        )


@pytest.mark.anyio
async def test_create_signup_existing_non_withdrawn():
    controller = SignupController.__new__(SignupController)
    session = SimpleNamespace(age_lower=5, age_upper=12)
    session_service = DummySessionService(session=session)
    student = SimpleNamespace(
        id=uuid4(), caregiver_id=uuid4(), date_of_birth=datetime(2016, 1, 1).date()
    )
    student_service = DummyStudentService(student=student)
    signup = SimpleNamespace(id=uuid4(), status="confirmed")
    signup_service = DummySignupService(signups=[signup])

    caregiver = SimpleNamespace(id=student.caregiver_id, name="Caregiver", phone="123")
    data = SignupCreateRequest(studentId=str(student.id))

    with pytest.raises(ValidationException):
        await SignupController.create_signup.fn(
            controller,
            uuid4(),
            data,
            signup_service,
            student_service,
            session_service,
            None,
            caregiver,
        )


@pytest.mark.anyio
async def test_create_signup_reactivate_withdrawn(monkeypatch):
    controller = SignupController.__new__(SignupController)
    session = SimpleNamespace(age_lower=5, age_upper=12)
    session_service = DummySessionService(session=session)
    student = SimpleNamespace(
        id=uuid4(), caregiver_id=uuid4(), date_of_birth=datetime(2016, 1, 1).date()
    )
    student_service = DummyStudentService(student=student)
    signup = SimpleNamespace(id=uuid4(), status="withdrawn")
    signup_service = DummySignupService(signups=[signup])

    class DummyQueue:
        async def enqueue(self, *args, **kwargs):
            return None

    async def fake_get_task_queue():
        return DummyQueue()

    monkeypatch.setattr(
        "app.domains.caregiver.controllers.signup.get_task_queue",
        fake_get_task_queue,
    )

    caregiver = SimpleNamespace(id=student.caregiver_id, name="Caregiver", phone="123")
    data = SignupCreateRequest(studentId=str(student.id), needsDevices=True)

    result = await SignupController.create_signup.fn(
        controller,
        uuid4(),
        data,
        signup_service,
        student_service,
        session_service,
        None,
        caregiver,
    )

    assert result.status == "pending"
    assert signup_service.updated


@pytest.mark.anyio
async def test_create_signup_new(monkeypatch):
    controller = SignupController.__new__(SignupController)
    session = SimpleNamespace(age_lower=5, age_upper=12)
    session_service = DummySessionService(session=session)
    student = SimpleNamespace(
        id=uuid4(), caregiver_id=uuid4(), date_of_birth=datetime(2016, 1, 1).date()
    )
    student_service = DummyStudentService(student=student)
    created = SimpleNamespace(id=uuid4())
    signup_service = DummySignupService(signups=[], create_result=created)

    class DummyQueue:
        async def enqueue(self, *args, **kwargs):
            return None

    async def fake_get_task_queue():
        return DummyQueue()

    monkeypatch.setattr(
        "app.domains.caregiver.controllers.signup.get_task_queue",
        fake_get_task_queue,
    )

    caregiver = SimpleNamespace(id=student.caregiver_id, name="Caregiver", phone="123")
    data = SignupCreateRequest(studentId=str(student.id))

    result = await SignupController.create_signup.fn(
        controller,
        uuid4(),
        data,
        signup_service,
        student_service,
        session_service,
        None,
        caregiver,
    )

    assert result.status == "pending"
    assert signup_service.created


@pytest.mark.anyio
async def test_withdraw_signup_not_found():
    controller = SignupController.__new__(SignupController)
    signup_service = DummySignupService()
    caregiver = SimpleNamespace(id=uuid4())

    with pytest.raises(NotFoundException):
        await SignupController.withdraw_signup.fn(
            controller, uuid4(), signup_service, caregiver
        )


@pytest.mark.anyio
async def test_withdraw_signup_already_withdrawn():
    controller = SignupController.__new__(SignupController)
    student = SimpleNamespace(caregiver_id=uuid4(), name="Student")
    session = SimpleNamespace(name="Session")
    signup = SimpleNamespace(status="withdrawn", student=student, session=session)

    class WithdrawService(DummySignupService):
        async def get(self, signup_id, load=None):
            return signup

    signup_service = WithdrawService()
    caregiver = SimpleNamespace(id=student.caregiver_id)

    result = await SignupController.withdraw_signup.fn(
        controller, uuid4(), signup_service, caregiver
    )
    assert result["message"] == "Signup already withdrawn"


@pytest.mark.anyio
async def test_withdraw_signup_success(monkeypatch):
    controller = SignupController.__new__(SignupController)
    student = SimpleNamespace(caregiver_id=uuid4(), name="Student")
    session = SimpleNamespace(name="Session")
    signup = SimpleNamespace(status="confirmed", student=student, session=session)

    class WithdrawService(DummySignupService):
        async def get(self, signup_id, load=None):
            return signup

    class DummyQueue:
        async def enqueue(self, *args, **kwargs):
            return None

    async def fake_get_task_queue():
        return DummyQueue()

    monkeypatch.setattr(
        "app.domains.caregiver.controllers.signup.get_task_queue",
        fake_get_task_queue,
    )

    signup_service = WithdrawService()
    caregiver = SimpleNamespace(
        id=student.caregiver_id, email="a@b.com", name="Caregiver"
    )

    result = await SignupController.withdraw_signup.fn(
        controller, uuid4(), signup_service, caregiver
    )
    assert result["message"] == "Signup withdrawn successfully"
    assert signup_service.updated
