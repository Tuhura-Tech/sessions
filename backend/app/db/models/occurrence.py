from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.session import Session
    from app.db.models.block import Block


class Occurrence(UUIDv7AuditBase):
    """A single scheduled occurrence of a session (e.g., weekly within a term)."""

    __tablename__ = "occurrences"

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_occurrences_time_valid"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Which block this occurrence belongs to",
    )

    session: Mapped[Session] = relationship("Session", back_populates="occurrences")
    block: Mapped[Block] = relationship("Block", back_populates="occurrences")
