from __future__ import annotations

from datetime import date as _date
from uuid import UUID

from pydantic import model_validator

from app.lib.schema import CamelizedBaseSchema


class ExclusionDate(CamelizedBaseSchema):
    id: UUID
    year: int
    date: _date
    reason: str | None = None


class ExclusionDateCreate(CamelizedBaseSchema):
    year: int
    date: _date
    reason: str | None = None


class ExclusionDateUpdate(CamelizedBaseSchema):
    year: int | None = None
    date: _date | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.year,
                self.date,
                self.reason,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
