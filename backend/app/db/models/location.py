from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advanced_alchemy.base import UUIDv7AuditBase


class Location(UUIDv7AuditBase):
    """A physical venue/location that may host multiple sessions."""

    __tablename__ = "locations"

    # Display fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    # Geo
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Instructions
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Internal information
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="location")
