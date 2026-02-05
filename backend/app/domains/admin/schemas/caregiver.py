from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import model_validator

from app.lib.schema import CamelizedBaseSchema

if TYPE_CHECKING:
    from app.domains.admin.schemas.student import StudentBase


class Caregiver(CamelizedBaseSchema):
    id: UUID
    email: str
    name: str | None = None
    phone: str | None = None
    email_verified: bool
    profile_complete: bool = False

    referral_source: str | None = None
    students: list["StudentBase"] = []


class CaregiverCreate(CamelizedBaseSchema):
    email: str
    name: str | None = None
    phone: str | None = None
    email_verified: bool
    referral_source: str | None = None
    email_verified: bool = False
    subscribe_newsletter: bool = False


class CaregiverUpdate(CamelizedBaseSchema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.name,
                self.email,
                self.phone,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class CaregiverMessage(CamelizedBaseSchema):
    subject: str
    message: str


# Rebuild the model after all imports are complete to resolve forward references
def _rebuild_caregiver_model() -> None:
    from app.domains.admin.schemas.student import StudentBase  # noqa: F401

    Caregiver.model_rebuild()


_rebuild_caregiver_model()
