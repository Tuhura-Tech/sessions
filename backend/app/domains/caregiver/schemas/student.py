from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import Field, model_validator

from app.lib.schema import CamelizedBaseSchema


class Student(CamelizedBaseSchema):
    id: UUID
    name: str
    date_of_birth: date

    media_consent: bool
    medical_info: str | None = None
    needs_devices: bool = False
    other_info: str | None = None
    archived: bool = False


class StudentCreate(CamelizedBaseSchema):
    name: str = Field(..., min_length=1)
    date_of_birth: date = Field(...)
    media_consent: bool = Field(False)
    medical_info: str | None = Field(None)
    needs_devices: bool = Field(False)
    other_info: str | None = Field(None)

    # Optional demographic information for reporting
    region: str | None = None
    ethnicity: str | None = None
    school_name: str | None = Field(None)


class StudentUpdate(CamelizedBaseSchema):
    name: str | None = Field(None, min_length=1)
    date_of_birth: date | None = Field(None)
    media_consent: bool | None = Field(None)
    medical_info: str | None = Field(None)
    other_info: str | None = Field(None)
    archived: bool | None = Field(None)

    # Optional demographic information for reporting
    region: str | None = None
    ethnicity: str | None = None
    school_name: str | None = Field(None)
    gender: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.name,
                self.date_of_birth,
                self.media_consent,
                self.medical_info,
                self.other_info,
                self.region,
                self.ethnicity,
                self.school_name,
                self.gender,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
