from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.student import Student
    from app.db.models.occurrence import Occurrence


from enum import StrEnum


class AttendanceStatus(StrEnum):
    """Enumeration of possible attendance statuses."""

    PRESENT = "present"
    ABSENT_KNOWN = "absent_known"
    ABSENT_UNKNOWN = "absent_unknown"


class AttendanceRecord(UUIDv7AuditBase):
    """Attendance for a student at a particular session occurrence."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('present','absent_known','absent_unknown')",
            name="ck_attendance_records_status",
        ),
    )

    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("occurrences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[AttendanceStatus] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurrence: Mapped[Occurrence] = relationship("Occurrence", lazy="selectin")
    student: Mapped[Student] = relationship("Student", lazy="selectin")
