from __future__ import annotations

import logging
import uuid

from advanced_alchemy.extensions.litestar import providers
from litestar import Controller, delete, get, patch, post
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ValidationException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.db import models as m
from app.domains.caregiver.guards import get_current_caregiver
from app.domains.caregiver.schemas.student import Student, StudentCreate, StudentUpdate
from app.domains.caregiver.services.auth import AuthSessionService
from app.domains.caregiver.services.caregiver import CaregiverService
from app.domains.caregiver.services.student import StudentService

logger = logging.getLogger(__name__)


class StudentController(Controller):
    """Caregiver student management endpoints."""

    path = "/api/v1/students"
    tags = ["Caregiver Students"]
    dependencies = providers.create_service_dependencies(
        StudentService,
        "student_service",
    )
    dependencies.update(
        providers.create_service_dependencies(
            CaregiverService,
            "caregiver_service",
        )
    )
    dependencies.update(
        providers.create_service_dependencies(
            AuthSessionService,
            "auth_session_service",
        )
    )
    dependencies.update(
        {
            "current_caregiver": Provide(get_current_caregiver),
        }
    )

    @get("/", status_code=HTTP_200_OK, summary="List students")
    async def list_students(
        self,
        student_service: StudentService,
        current_caregiver: m.Caregiver,
    ) -> list[Student]:
        """List all students belonging to the current caregiver."""
        students = await student_service.list(
            m.Student.caregiver_id == current_caregiver.id
        )
        return [
            student_service.to_schema(student, schema_type=Student)
            for student in students
        ]

    @post("/", status_code=HTTP_201_CREATED, summary="Create student")
    async def create_student(
        self,
        data: StudentCreate,
        student_service: StudentService,
        current_caregiver: m.Caregiver,
    ) -> Student:
        """Create a new student record for the current caregiver."""
        if not current_caregiver.name or not current_caregiver.phone:
            raise ValidationException(
                detail="Complete your profile (name and phone) before adding students."
            )

        new_student = await student_service.create(
            {
                "caregiver_id": current_caregiver.id,
                "name": data.name,
                "date_of_birth": data.date_of_birth,
                "media_consent": data.media_consent,
                "medical_info": data.medical_info,
                "needs_devices": data.needs_devices,
                "other_info": data.other_info,
                "region": data.region,
                "ethnicity": data.ethnicity,
                "school_name": data.school_name,
            },
            auto_commit=True,
        )
        logger.info(
            "Created student %s for caregiver %s",
            new_student.id,
            current_caregiver.id,
        )

        return student_service.to_schema(new_student, schema_type=Student)

    @get("/{student_id:uuid}", status_code=HTTP_200_OK, summary="Get student")
    async def get_student(
        self,
        student_id: uuid.UUID,
        student_service: StudentService,
        current_caregiver: m.Caregiver,
    ) -> Student:
        """Get a specific student record."""
        student = await student_service.get(student_id)
        if not student or student.caregiver_id != current_caregiver.id:
            raise NotFoundException(detail="Student not found")

        return student_service.to_schema(student, schema_type=Student)

    @patch("/{student_id:uuid}", status_code=HTTP_200_OK, summary="Update student")
    async def update_student(
        self,
        student_id: uuid.UUID,
        data: StudentUpdate,
        student_service: StudentService,
        current_caregiver: m.Caregiver,
    ) -> Student:
        """Update a student record."""
        student = await student_service.get(student_id)
        if not student or student.caregiver_id != current_caregiver.id:
            raise NotFoundException(detail="Student not found")

        update_data = data.model_dump(exclude_unset=True)
        updated_student = await student_service.update(
            update_data,
            student_id,
            auto_commit=True,
        )
        logger.info("Updated student %s", student_id)

        return student_service.to_schema(updated_student, schema_type=Student)

    @delete("/{student_id:uuid}", status_code=HTTP_200_OK, summary="Delete student")
    async def delete_student(
        self,
        student_id: uuid.UUID,
        student_service: StudentService,
        current_caregiver: m.Caregiver,
    ) -> dict:
        """Delete a student record (also withdraws all associated signups)."""
        student = await student_service.get(student_id)
        if not student or student.caregiver_id != current_caregiver.id:
            raise NotFoundException(detail="Student not found")

        await student_service.delete(student_id, auto_commit=True)
        logger.info("Deleted student %s", student_id)

        return {"message": "Student deleted successfully"}
