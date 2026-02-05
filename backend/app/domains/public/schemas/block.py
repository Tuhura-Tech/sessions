from __future__ import annotations

from datetime import date
from uuid import UUID

from app.lib.schema import CamelizedBaseSchema


class Block(CamelizedBaseSchema):
    id: UUID
    year: int
    name: str
    start_date: date
    end_date: date
    block_type: str  # special, term_1, term_2, term_3, term_4
