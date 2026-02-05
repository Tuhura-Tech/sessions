from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.session import Session
    from app.db.models.staff import Staff


class SessionStaff(UUIDv7AuditBase):
    """Association table for assigning staff members to sessions.

    Represents the many-to-many relationship between sessions and staff.
    A session can have multiple staff members, and a staff member can be
    assigned to multiple sessions.
    """

    __tablename__ = "session_staff"

    __table_args__ = (
        UniqueConstraint("session_id", "staff_id", name="uq_session_staff"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Track when this assignment was made
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    session: Mapped[Session] = relationship(
        "Session", back_populates="session_staff_assignments"
    )
    staff: Mapped[Staff] = relationship("Staff", back_populates="session_assignments")
