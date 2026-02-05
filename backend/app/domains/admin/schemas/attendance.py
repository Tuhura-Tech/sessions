from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.lib.schema import CamelizedBaseSchema

AttendanceStatus = Literal["present", "absent_known", "absent_unknown"]


class AttendanceRecord(CamelizedBaseSchema):
    """Attendance record for a student at an occurrence."""

    id: UUID
    occurrence_id: UUID
    student_id: UUID
    status: AttendanceStatus
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AttendanceUpsert(CamelizedBaseSchema):
    """Request to mark or update attendance for a student."""

    student_id: UUID
    status: AttendanceStatus
    reason: str | None = None


class AttendanceRollItem(CamelizedBaseSchema):
    """Single student item in an attendance roll."""

    signup_id: UUID
    student_id: UUID
    student_name: str
    caregiver_name: str
    attendance: AttendanceRecord | None = None


class AttendanceRoll(CamelizedBaseSchema):
    """Complete attendance roll for an occurrence."""

    occurrence_id: UUID
    session_id: UUID
    starts_at: datetime
    ends_at: datetime
    cancelled: bool
    items: list[AttendanceRollItem]
