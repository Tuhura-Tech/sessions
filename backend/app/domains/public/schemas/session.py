from __future__ import annotations

from datetime import time
from uuid import UUID

from app.lib.schema import CamelizedBaseSchema

from app.domains.public.schemas.occurrence import Occurrence


class Location(CamelizedBaseSchema):
    name: str
    address: str
    region: str
    lat: float
    lng: float


class BlockOccurrences(CamelizedBaseSchema):
    block_id: UUID
    block_name: str
    block_type: str
    occurrences: list[Occurrence]


class Session(CamelizedBaseSchema):
    id: UUID
    name: str
    year: int
    age_lower: int
    age_upper: int
    day_of_week: int | None
    start_time: time
    end_time: time
    # waitlist: bool
    what_to_bring: str | None
    prerequisites: str | None

    blocks: list[str] = []
    location: Location


class SessionDetail(Session):
    occurrences: list[Occurrence] = []
    occurrences_by_block: list[BlockOccurrences] = []
