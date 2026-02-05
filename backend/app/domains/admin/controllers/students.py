from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, delete, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK

from app.domains.admin.schemas.signup import Signup
from app.domains.admin.schemas.student import Student, StudentCreate, StudentUpdate
from sqlalchemy.orm import joinedload, selectinload
from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.services.student import StudentService

logger = logging.getLogger(__name__)


class StudentController(Controller):
    """Admin endpoints for managing students."""

    path = "/api/v1/admin/students"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        StudentService,
        "student_service",
        # enable to filter by region, by min age, by max_age and by location
        load=[
            selectinload(m.Student.caregiver).options(
                joinedload(m.Caregiver.students, innerjoin=True),
            ),
            selectinload(m.Student.signups).options(
                joinedload(m.Signup.session, innerjoin=True),
                selectinload(m.Signup.student).selectinload(m.Student.caregiver),
            ),
        ],
    )

    @get("/")
    async def list_students(
        self,
        student_service: StudentService,
        limit: int = 100,
        offset: int = 0,
    ) -> service.OffsetPagination[Student]:
        """List all students with pagination.
        
        Args:
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)
        """
        results, total = await student_service.list_and_count(LimitOffset(limit, offset))
        return student_service.to_schema(results, total, schema_type=Student)

    @get("/{student_id:uuid}")
    async def get_student(
        self,
        student_id: UUID,
        student_service: StudentService,
    ) -> Student:
        """Get a single student by ID."""
        student = await student_service.get(student_id)
        if not student:
            raise NotFoundException(detail="Student not found")
        return student_service.to_schema(student, schema_type=Student)

    @post("/")
    async def create_student(
        self,
        data: StudentCreate,
        student_service: StudentService,
    ) -> Student:
        """Create a new student."""
        student = await student_service.create(data, auto_commit=True)
        # fetch it again with the caregiver relationship
        student = await student_service.get(student.id)
        return student_service.to_schema(student, schema_type=Student)

    @patch("/{student_id:uuid}")
    async def update_student(
        self,
        student_id: UUID,
        data: StudentUpdate,
        student_service: StudentService,
    ) -> Student:
        """Update an existing student."""
        student = await student_service.update(
            data.model_dump(exclude_unset=True), student_id
        )
        if not student:
            raise NotFoundException(detail="Student not found")
        return student_service.to_schema(student, schema_type=Student)

    @delete("/{student_id:uuid}", status_code=HTTP_200_OK)
    async def delete_student(
        self,
        student_id: UUID,
        student_service: StudentService,
    ) -> None:
        """Delete a student."""
        deleted = await student_service.delete(student_id)
        if not deleted:
            raise NotFoundException(detail="Student not found")

    @get("/{student_id:uuid}/signups", status_code=HTTP_200_OK)
    async def get_student_signups(
        self,
        student_id: UUID,
        student_service: StudentService,
    ) -> service.OffsetPagination[Signup]:
        """Get all signup IDs for a specific student."""
        student = await student_service.get(student_id)
        if not student:
            raise NotFoundException(detail="Student not found")

        signups = await student_service.get_student_signups(student)

        return student_service.to_schema(signups, len(signups), schema_type=Signup)
