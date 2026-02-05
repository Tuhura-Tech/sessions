from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.caregiver import Caregiver


class CaregiverMagicLink(UUIDv7AuditBase):
    """Single-use, time-limited magic link token for caregiver login."""

    __tablename__ = "caregiver_magic_links"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("caregivers.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    caregiver: Mapped[Caregiver] = relationship("Caregiver", lazy="selectin")


class CaregiverSession(UUIDv7AuditBase):
    """Authenticated caregiver browser sessions."""

    __tablename__ = "caregiver_sessions"

    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("caregivers.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    caregiver: Mapped[Caregiver] = relationship("Caregiver", lazy="selectin")
