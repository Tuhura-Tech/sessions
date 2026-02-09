from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models.student import Student


class Caregiver(UUIDv7AuditBase):
    """Caregiver account authenticated via magic link (passwordless)."""

    __tablename__ = "caregivers"

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    referral_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    students: Mapped[list[Student]] = relationship(
        "Student",
        back_populates="caregiver",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
