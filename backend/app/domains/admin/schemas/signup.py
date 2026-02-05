from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Mapping
from uuid import UUID

from pydantic import model_validator

from app.domains.admin.schemas.student import StudentBase
from app.lib.schema import CamelizedBaseSchema


class SignupStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    WITHDRAWN = "withdrawn"


class Signup(CamelizedBaseSchema):
    id: UUID
    student_id: UUID
    session_id: UUID
    status: SignupStatus
    withdrawn_at: datetime | None = None
    pickup_dropoff: str | None = None
    created_at: datetime | None = None
    needs_devices: bool = False
    student_name: str | None = None
    guardian_name: str | None = None
    email: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    media_consent: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def hydrate_related_fields(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            return data

        student = getattr(data, "student", None)
        caregiver = getattr(student, "caregiver", None) if student else None

        payload = {
            "id": data.id,
            "student_id": data.student_id,
            "session_id": data.session_id,
            "status": data.status,
            "withdrawn_at": data.withdrawn_at,
            "pickup_dropoff": data.pickup_dropoff,
            "created_at": getattr(data, "created_at", None),
            "needs_devices": getattr(data, "needs_devices", False),
            "student_name": getattr(student, "name", None),
            "guardian_name": getattr(caregiver, "name", None),
            "email": getattr(caregiver, "email", None),
            "phone": getattr(caregiver, "phone", None),
            "date_of_birth": getattr(student, "date_of_birth", None),
            "media_consent": getattr(student, "media_consent", None),
        }

        if "student" in cls.model_fields:
            payload["student"] = student

        return payload


class SignupStudent(Signup):
    student: StudentBase


class SignupCreate(CamelizedBaseSchema):
    status: SignupStatus = SignupStatus.WAITLISTED
    pickup_dropoff: str | None = None
    student_id: UUID
    session_id: UUID


class SignupUpdate(CamelizedBaseSchema):
    status: SignupStatus | None = None
    pickup_dropoff: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.status,
                self.pickup_dropoff,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SignupStatusUpdate(CamelizedBaseSchema):
    """Update only the status of a signup with optional metadata."""

    status: SignupStatus
    reason: str | None = None
    notify_caregiver: bool = False
