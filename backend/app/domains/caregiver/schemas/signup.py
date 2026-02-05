from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.lib.schema import CamelizedBaseSchema


SignupStatus = Literal["pending", "confirmed", "waitlisted", "withdrawn"]


class SignupBase(CamelizedBaseSchema):
    """Base signup schema with common fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: SignupStatus
    created_at: datetime
    withdrawn_at: datetime | None = None
    pickup_dropoff: str | None = None
    needs_devices: bool = False


class SignupWithSession(SignupBase):
    """Signup with session details."""

    session_id: UUID
    session_name: str


class SignupWithStudent(SignupBase):
    """Signup with student details."""

    student_id: UUID
    student_name: str


class SignupFull(SignupBase):
    """Signup with both session and student details."""

    session_id: UUID
    session_name: str
    student_id: UUID
    student_name: str


class SignupCreateRequest(CamelizedBaseSchema):
    """Request body for creating a signup to a session."""

    model_config = ConfigDict(from_attributes=True)

    student_id: str = Field(..., alias="studentId")
    pickup_dropoff: str | None = Field(None, alias="pickupDropoff")
    needs_devices: bool = Field(False, alias="needsDevices")


class SignupCreateResponse(CamelizedBaseSchema):
    """Response after creating a signup."""

    id: str
    status: SignupStatus
