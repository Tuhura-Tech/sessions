from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.db.models.block_link import BlockLink
    from app.db.models.occurrence import Occurrence


class Block(UUIDv7AuditBase):
    """A block (term or special) with a defined date range per year.

    Sessions link to blocks via BlockLink.
    Occurrences belong to blocks via block_id.
    """

    __tablename__ = "blocks"

    __table_args__ = (UniqueConstraint("year", "name", name="uq_blocks_year_name"),)

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Display name (e.g., "Term 1", "Summer Special")
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Block type (special, term_1, term_2, term_3, term_4)
    block_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="special", server_default="special"
    )

    # Date range for this block
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    block_links: Mapped[list[BlockLink]] = relationship(
        "BlockLink", back_populates="block", cascade="all, delete-orphan"
    )

    occurrences: Mapped[list[Occurrence]] = relationship(
        "Occurrence", back_populates="block"
    )

    def __repr__(self) -> str:
        return f"Block(year={self.year}, name={self.name!r})"
