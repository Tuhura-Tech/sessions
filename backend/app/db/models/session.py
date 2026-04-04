from __future__ import annotations

import enum
import uuid
from datetime import time
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models.block_link import BlockLink
    from app.db.models.location import Location
    from app.db.models.occurrence import Occurrence
    from app.db.models.session_staff import SessionStaff
    from app.db.models.signup import Signup


class DayOfWeekEnum(enum.IntEnum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class Session(UUIDv7AuditBase):
    """A session definition.

    Session types:
    - term: a year-long weekly session (runs during school terms).
    - special: a one-off program with a custom set of occurrences.
    - event: a one-off event (shown on the public events page).
    """

    __tablename__ = "sessions"

    __table_args__ = (
        CheckConstraint(
            "session_type IN ('term','special','event')", name="ck_sessions_type"
        ),
        CheckConstraint(
            "day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6",
            name="ck_sessions_day_of_week_nullable",
        ),
        CheckConstraint(
            "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special') OR (session_type = 'event')",
            name="ck_sessions_term_requires_schedule",
        ),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("locations.id"), nullable=False
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="term", index=True
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Age details
    age_lower: Mapped[int] = mapped_column(Integer, nullable=False)
    age_upper: Mapped[int] = mapped_column(Integer, nullable=False)

    # Day of week (0=Sun .. 6=Sat)
    day_of_week: Mapped[DayOfWeekEnum | None] = mapped_column(Integer, nullable=True)

    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Whether new signups are placed on the waitlist regardless of capacity.
    # When True, the session is in "waitlist mode" and age-eligible signups are
    # waitlisted even if there are still confirmed spots available.
    waitlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Public venue info
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Staff-only (not exposed in public endpoints)
    photo_album_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # Relationships
    location: Mapped[Location] = relationship("Location", back_populates="sessions")
    signups: Mapped[list[Signup]] = relationship(
        "Signup", back_populates="session", lazy="selectin"
    )

    occurrences: Mapped[list[Occurrence]] = relationship(
        "Occurrence",
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    block_links: Mapped[list[BlockLink]] = relationship(
        "BlockLink",
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    session_staff_assignments: Mapped[list[SessionStaff]] = relationship(
        "SessionStaff",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    @property
    def blocks(self) -> list:
        """Get all blocks this session runs in, ordered by date."""
        from app.db.models.block import Block

        blocks: list[Block] = [link.block for link in self.block_links]
        return sorted(blocks, key=lambda b: (b.year, b.name))

    @property
    def occurrences_by_block(self) -> dict:
        """Get occurrences organized by block."""
        result = {}
        for occurrence in self.occurrences:
            if occurrence.block_id:
                if occurrence.block_id not in result:
                    result[occurrence.block_id] = []
                result[occurrence.block_id].append(occurrence)
        return result

    @property
    def confirmed_count(self) -> int:
        """Count confirmed signups."""
        return sum(1 for s in self.signups if s.status == "confirmed")

    @property
    def waitlist_count(self) -> int:
        """Count waitlisted signups."""
        return sum(1 for s in self.signups if s.status == "waitlisted")

    @property
    def pending_count(self) -> int:
        """Count pending signups."""
        return sum(1 for s in self.signups if s.status == "pending")

    @property
    def needs_devices_count(self) -> int:
        """Count signups needing devices."""
        return sum(1 for s in self.signups if s.needs_devices)

    @property
    def is_full(self) -> bool:
        """Check if session is full or explicitly in waitlist mode."""
        return self.waitlist or self.confirmed_count >= self.capacity
