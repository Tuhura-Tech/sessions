from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import model_validator

from app.lib.schema import CamelizedBaseSchema


class Occurrence(CamelizedBaseSchema):
    id: UUID

    starts_at: datetime
    ends_at: datetime

    cancelled: bool
    block_id: UUID
    session_id: UUID
    cancellation_reason: str | None = None


class OccurrenceCreate(CamelizedBaseSchema):
    starts_at: datetime
    ends_at: datetime
    session_id: UUID
    block_id: UUID


class OccurrenceUpdate(CamelizedBaseSchema):
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    cancelled: bool | None = None
    cancellation_reason: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.starts_at,
                self.ends_at,
                self.cancelled,
                self.cancellation_reason,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
