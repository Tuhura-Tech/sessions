from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import model_validator

from app.domains.admin.schemas.caregiver import Caregiver
from app.lib.schema import CamelizedBaseSchema


class StudentBase(CamelizedBaseSchema):
    id: UUID
    name: str | None = None
    date_of_birth: date | None = None

    media_consent: bool | None = None
    medical_info: str | None = None
    other_info: str | None = None
    archived: bool = False


class Student(StudentBase):
    caregiver: Caregiver


class StudentCreate(CamelizedBaseSchema):
    caregiver_id: UUID
    name: str
    date_of_birth: date

    media_consent: bool
    medical_info: str | None = None
    other_info: str | None = None

    region: str | None = None
    ethnicity: str | None = None
    school_name: str | None = None
    gender: str | None = None


class StudentUpdate(CamelizedBaseSchema):
    name: str | None = None
    date_of_birth: date | None = None
    media_consent: bool | None = None
    medical_info: str | None = None
    other_info: str | None = None
    archived: bool | None = None

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
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
