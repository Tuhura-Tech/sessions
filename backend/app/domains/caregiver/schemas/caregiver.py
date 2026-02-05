from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field

from app.lib.schema import CamelizedBaseSchema


class CaregiverMe(CamelizedBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    phone: str | None = None
    email_verified: bool = False
    profile_complete: bool = False


class CaregiverUpdate(CamelizedBaseSchema):
    name: str | None = Field(None, min_length=0)
    phone: str | None = Field(None, min_length=0)
    subscribe_newsletter: bool = Field(False)
    referral_source: str | None = Field(None)
