from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import model_validator

from app.lib.schema import CamelizedBaseSchema


class Block(CamelizedBaseSchema):
    id: UUID
    year: int
    name: str
    block_type: str
    start_date: date
    end_date: date


class BlockCreate(CamelizedBaseSchema):
    year: int
    name: str
    block_type: str
    start_date: date
    end_date: date


class BlockUpdate(CamelizedBaseSchema):
    start_date: date | None = None
    end_date: date | None = None
    year: int | None = None
    name: str | None = None
    block_type: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.year,
                self.name,
                self.block_type,
                self.start_date,
                self.end_date,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
