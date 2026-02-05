from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase

if TYPE_CHECKING:
    from app.db.models.session_staff import SessionStaff


class Staff(UUIDv7AuditBase):
    """Staff members who can be assigned to sessions.

    Staff are authenticated via SSO and their details (name, email)
    are synced from the SSO provider.
    """

    __tablename__ = "staff"

    # SSO-provided fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # SSO identifier (e.g., sub claim from OIDC)
    sso_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # Last time this staff member logged in
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete for deactivated staff
    active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    session_assignments: Mapped[list[SessionStaff]] = relationship(
        "SessionStaff",
        back_populates="staff",
        cascade="all, delete-orphan",
    )
