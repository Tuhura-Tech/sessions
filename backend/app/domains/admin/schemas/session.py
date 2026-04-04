from __future__ import annotations

from datetime import time
from typing import Any, Mapping, Literal
from uuid import UUID

from pydantic import ConfigDict, field_validator, model_validator

from app.domains.admin.schemas.location import Location
from app.lib.schema import CamelizedBaseSchema
from app.lib.validation import (
    validate_age_range,
    validate_capacity,
    validate_time_range,
)


class Session(CamelizedBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year: int
    session_type: Literal["term", "special", "event"]
    name: str
    age_lower: int
    age_upper: int

    start_time: time
    end_time: time

    day_of_week: int | None = None

    capacity: int
    waitlist: bool = False

    description: str | None = None

    photo_album_url: str | None = None
    internal_notes: str | None = None

    archived: bool

    location_id: UUID
    location: Location | None = None

    confirmed_count: int = 0
    waitlist_count: int = 0
    pending_count: int = 0
    is_full: bool = False
    needs_devices_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_signup_counts(cls, data: Any) -> Any:
        """Compute signup counts from signups relationship if not already set."""
        # If it's not a dict, it will be handled by Pydantic's from_attributes
        if not isinstance(data, Mapping):
            return data

        payload: dict[str, Any] = dict(data)

        # If counts are already set and non-zero, use them
        if (
            payload.get("confirmed_count", 0) > 0
            or payload.get("waitlist_count", 0) > 0
            or payload.get("pending_count", 0) > 0
        ):
            return payload

        # Try to compute from signups relationship if available
        signups = payload.get("signups", [])
        if signups:
            confirmed = sum(
                1
                for s in signups
                if (
                    s.get("status")
                    if isinstance(s, dict)
                    else getattr(s, "status", None)
                )
                == "confirmed"
            )
            waitlisted = sum(
                1
                for s in signups
                if (
                    s.get("status")
                    if isinstance(s, dict)
                    else getattr(s, "status", None)
                )
                == "waitlisted"
            )
            pending = sum(
                1
                for s in signups
                if (
                    s.get("status")
                    if isinstance(s, dict)
                    else getattr(s, "status", None)
                )
                == "pending"
            )

            payload["confirmed_count"] = confirmed
            payload["waitlist_count"] = waitlisted
            payload["pending_count"] = pending
            payload["is_full"] = confirmed >= (payload.get("capacity", 0) or 0)

        return payload


class SessionCreate(CamelizedBaseSchema):
    year: int
    session_type: Literal["term", "special", "event"]
    name: str
    age_lower: int
    age_upper: int

    start_time: time
    end_time: time
    day_of_week: int | None = None

    capacity: int
    waitlist: bool = False

    description: str | None = None

    photo_album_url: str | None = None
    internal_notes: str | None = None

    archived: bool = False

    location_id: UUID
    blocks: list[UUID]
    generate_occurrences: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate session name is not empty."""
        if not v or not v.strip():
            raise ValueError("Session name is required")
        if len(v) > 255:
            raise ValueError("Session name cannot exceed 255 characters")
        return v.strip()

    @field_validator("capacity")
    @classmethod
    def validate_capacity_value(cls, v: int) -> int:
        """Validate capacity."""
        validate_capacity(v)
        return v

    @model_validator(mode="after")
    def validate_times_and_ages(self) -> SessionCreate:
        """Validate time and age ranges."""
        if self.session_type == "term" and self.day_of_week is None:
            raise ValueError("day_of_week is required for term sessions")

        validate_time_range(self.start_time, self.end_time)
        validate_age_range(self.age_lower, self.age_upper)
        return self


class SessionUpdate(CamelizedBaseSchema):
    year: int | None = None
    session_type: Literal["term", "special", "event"] | None = None
    name: str | None = None
    age_lower: int | None = None
    age_upper: int | None = None

    start_time: time | None = None
    end_time: time | None = None
    day_of_week: int | None = None

    capacity: int | None = None
    waitlist: bool | None = None

    description: str | None = None

    photo_album_url: str | None = None
    internal_notes: str | None = None

    archived: bool | None = None

    location_id: UUID | None = None

    @field_validator("capacity")
    @classmethod
    def validate_capacity_if_provided(cls, v: int | None) -> int | None:
        """Validate capacity if provided."""
        if v is not None:
            validate_capacity(v)
        return v

    @model_validator(mode="after")
    def validate_times_and_ages_if_provided(self) -> SessionUpdate:
        """Validate time and age ranges if provided."""
        if self.start_time is not None and self.end_time is not None:
            validate_time_range(self.start_time, self.end_time)

        if self.age_lower is not None and self.age_upper is not None:
            validate_age_range(self.age_lower, self.age_upper)
        elif self.age_lower is not None or self.age_upper is not None:
            # If only one is provided, validate it exists
            if self.age_lower is not None and self.age_lower < 0:
                raise ValueError("Minimum age cannot be negative")
            if self.age_upper is not None and self.age_upper > 150:
                raise ValueError("Maximum age cannot exceed 150")

        return self

    @model_validator(mode="after")
    def at_least_one_field(self) -> SessionUpdate:
        """Ensure at least one field is provided for update."""
        if all(
            v is None
            for v in [
                self.year,
                self.session_type,
                self.name,
                self.age_lower,
                self.age_upper,
                self.start_time,
                self.end_time,
                self.capacity,
                self.description,
                self.photo_album_url,
                self.internal_notes,
                self.archived,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SessionEmail(CamelizedBaseSchema):
    subject: str
    message: str
