from __future__ import annotations

from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from app.lib.schema import CamelizedBaseSchema


class Location(CamelizedBaseSchema):
    id: UUID
    name: str
    address: str
    region: str
    lat: float
    lng: float
    instructions: str | None = None

    contact_name: str = Field(..., alias="contactName")
    contact_email: EmailStr = Field(..., alias="contactEmail")
    contact_phone: str | None = Field(None, alias="contactPhone")
    internal_notes: str | None = Field(None, alias="internalNotes")


class LocationCreate(CamelizedBaseSchema):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    lat: float = Field(...)
    lng: float = Field(...)
    instructions: str | None = None

    contact_name: str = Field(..., alias="contactName", min_length=1)
    contact_email: EmailStr = Field(..., alias="contactEmail")
    contact_phone: str | None = Field(None, alias="contactPhone")
    internal_notes: str | None = Field(None, alias="internalNotes")


class LocationUpdate(CamelizedBaseSchema):
    name: str | None = None
    address: str | None = None
    region: str | None = None
    lat: float | None = None
    lng: float | None = None
    instructions: str | None = None

    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    internal_notes: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            v is None
            for v in [
                self.name,
                self.address,
                self.region,
                self.lat,
                self.lng,
                self.instructions,
                self.contact_name,
                self.contact_email,
                self.contact_phone,
                self.internal_notes,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self
