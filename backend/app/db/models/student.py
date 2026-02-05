from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models.attendance import AttendanceRecord
    from app.db.models.caregiver import Caregiver
    from app.db.models.signup import Signup


class Student(UUIDv7AuditBase):
    """Student records derived from signups for operational continuity."""

    __tablename__ = "students"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("caregivers.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    media_consent: Mapped[bool] = mapped_column(nullable=False, default=False)
    medical_info: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    other_info: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Demographic information for reporting (NEVER exposed to staff)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status tracking
    archived: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Relationships
    caregiver: Mapped[Caregiver] = relationship("Caregiver", back_populates="students")
    signups: Mapped[list[Signup]] = relationship("Signup", back_populates="student")
    attendence_records: Mapped[list[AttendanceRecord]] = relationship(
        "AttendanceRecord", back_populates="student"
    )
