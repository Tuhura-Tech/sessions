"""
Unit tests for caregiver student controller logic.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from litestar.exceptions import NotFoundException, ValidationException

from app.domains.caregiver.controllers.student import StudentController
from app.domains.caregiver.schemas.student import StudentCreate, StudentUpdate


class DummyStudentService:
    def __init__(self, student=None, updated=None, created=None):
        self.student = student
        self.updated = updated
        self.created = created
        self.deleted = []

    async def list(self, *args, **kwargs):
        return [self.student] if self.student else []

    async def get(self, student_id):
        return self.student

    async def create(self, data, auto_commit=False):
        return self.created

    async def update(self, data, student_id, auto_commit=False):
        return self.updated

    async def delete(self, student_id, auto_commit=False):
        self.deleted.append(student_id)
        return True

    def to_schema(self, student, schema_type):
        return {"id": str(student.id), "name": student.name}


@pytest.mark.anyio
async def test_list_students_returns_schema():
    controller = StudentController.__new__(StudentController)
    student = SimpleNamespace(id=uuid4(), caregiver_id=uuid4(), name="Student")
    service = DummyStudentService(student=student)
    caregiver = SimpleNamespace(id=student.caregiver_id)

    results = await StudentController.list_students.fn(controller, service, caregiver)
    assert results[0]["name"] == "Student"


@pytest.mark.anyio
async def test_create_student_requires_profile():
    controller = StudentController.__new__(StudentController)
    service = DummyStudentService()
    caregiver = SimpleNamespace(id=uuid4(), name=None, phone=None)
    data = StudentCreate(name="Student", date_of_birth=date(2016, 1, 1))

    with pytest.raises(ValidationException):
        await StudentController.create_student.fn(controller, data, service, caregiver)


@pytest.mark.anyio
async def test_create_student_success():
    controller = StudentController.__new__(StudentController)
    created = SimpleNamespace(id=uuid4(), name="Student")
    service = DummyStudentService(created=created)
    caregiver = SimpleNamespace(id=uuid4(), name="Caregiver", phone="123")
    data = StudentCreate(name="Student", date_of_birth=date(2016, 1, 1))

    result = await StudentController.create_student.fn(
        controller, data, service, caregiver
    )
    assert result["name"] == "Student"


@pytest.mark.anyio
async def test_get_student_not_found():
    controller = StudentController.__new__(StudentController)
    service = DummyStudentService(student=None)
    caregiver = SimpleNamespace(id=uuid4())

    with pytest.raises(NotFoundException):
        await StudentController.get_student.fn(controller, uuid4(), service, caregiver)


@pytest.mark.anyio
async def test_get_student_not_owned():
    controller = StudentController.__new__(StudentController)
    student = SimpleNamespace(id=uuid4(), caregiver_id=uuid4(), name="Student")
    service = DummyStudentService(student=student)
    caregiver = SimpleNamespace(id=uuid4())

    with pytest.raises(NotFoundException):
        await StudentController.get_student.fn(
            controller, student.id, service, caregiver
        )


@pytest.mark.anyio
async def test_update_student_success():
    controller = StudentController.__new__(StudentController)
    student = SimpleNamespace(id=uuid4(), caregiver_id=uuid4(), name="Student")
    updated = SimpleNamespace(id=student.id, name="Updated")
    service = DummyStudentService(student=student, updated=updated)
    caregiver = SimpleNamespace(id=student.caregiver_id)
    data = StudentUpdate(name="Updated")

    result = await StudentController.update_student.fn(
        controller, student.id, data, service, caregiver
    )
    assert result["name"] == "Updated"


@pytest.mark.anyio
async def test_update_student_not_found():
    controller = StudentController.__new__(StudentController)
    service = DummyStudentService(student=None)
    caregiver = SimpleNamespace(id=uuid4())
    data = StudentUpdate(name="Updated")

    with pytest.raises(NotFoundException):
        await StudentController.update_student.fn(
            controller, uuid4(), data, service, caregiver
        )


@pytest.mark.anyio
async def test_delete_student_success():
    controller = StudentController.__new__(StudentController)
    student = SimpleNamespace(id=uuid4(), caregiver_id=uuid4())
    service = DummyStudentService(student=student)
    caregiver = SimpleNamespace(id=student.caregiver_id)

    result = await StudentController.delete_student.fn(
        controller, student.id, service, caregiver
    )
    assert result["message"] == "Student deleted successfully"


@pytest.mark.anyio
async def test_delete_student_not_found():
    controller = StudentController.__new__(StudentController)
    service = DummyStudentService(student=None)
    caregiver = SimpleNamespace(id=uuid4())

    with pytest.raises(NotFoundException):
        await StudentController.delete_student.fn(
            controller, uuid4(), service, caregiver
        )
