from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.student import Student
    from app.db.models.session import Session


SignupStatus = Literal["pending", "confirmed", "waitlisted", "withdrawn"]


class Signup(UUIDv7AuditBase):
    """A caregiver's submission for a student to attend a session."""

    __tablename__ = "signups"

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_signups_session_student"),
        CheckConstraint(
            "status IN ('pending','confirmed','waitlisted','withdrawn')",
            name="ck_signups_status",
        ),
    )

    # Foreign keys
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("sessions.id"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("students.id"), nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pickup_dropoff: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_devices: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Relationships
    session: Mapped[Session] = relationship("Session", back_populates="signups")
    student: Mapped[Student] = relationship("Student", back_populates="signups")
