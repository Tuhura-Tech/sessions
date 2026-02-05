from __future__ import annotations


from app.lib.schema import CamelizedBaseSchema
from uuid import UUID
from datetime import datetime


class Occurrence(CamelizedBaseSchema):
    starts_at: datetime
    ends_at: datetime

    cancelled: bool
    block_id: UUID
    session_id: UUID
    cancellation_reason: str | None = None
