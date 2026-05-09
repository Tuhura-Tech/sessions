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

    block_ids: list[UUID] = []

    confirmed_count: int = 0
    waitlist_count: int = 0
    pending_count: int = 0
    is_full: bool = False
    needs_devices_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_fields(cls, data: Any) -> Any:
        """Compute block_ids and signup counts from ORM relationships."""
        # For ORM objects (from_attributes), convert to dict-like via __dict__
        if not isinstance(data, Mapping):
            block_links = getattr(data, "block_links", None) or []
            block_ids = [link.block_id for link in block_links]
            signups = getattr(data, "signups", None) or []
            confirmed = sum(
                1 for s in signups if getattr(s, "status", None) == "confirmed"
            )
            waitlisted = sum(
                1 for s in signups if getattr(s, "status", None) == "waitlisted"
            )
            pending = sum(1 for s in signups if getattr(s, "status", None) == "pending")
            capacity = getattr(data, "capacity", 0) or 0
            waitlist_flag = getattr(data, "waitlist", False)
            return {
                "id": getattr(data, "id"),
                "year": getattr(data, "year"),
                "session_type": getattr(data, "session_type"),
                "name": getattr(data, "name"),
                "age_lower": getattr(data, "age_lower"),
                "age_upper": getattr(data, "age_upper"),
                "start_time": getattr(data, "start_time"),
                "end_time": getattr(data, "end_time"),
                "day_of_week": getattr(data, "day_of_week", None),
                "capacity": capacity,
                "waitlist": waitlist_flag,
                "description": getattr(data, "description", None),
                "photo_album_url": getattr(data, "photo_album_url", None),
                "internal_notes": getattr(data, "internal_notes", None),
                "archived": getattr(data, "archived"),
                "location_id": getattr(data, "location_id"),
                "location": getattr(data, "location", None),
                "block_ids": block_ids,
                "confirmed_count": confirmed,
                "waitlist_count": waitlisted,
                "pending_count": pending,
                "is_full": bool(waitlist_flag) or confirmed >= capacity,
                "needs_devices_count": sum(
                    1 for s in signups if getattr(s, "needs_devices", False)
                ),
            }

        payload: dict[str, Any] = dict(data)

        # Populate block_ids from block_links if not already set
        if not payload.get("block_ids"):
            block_links = payload.get("block_links", [])
            if block_links:
                payload["block_ids"] = [
                    link.get("block_id")
                    if isinstance(link, dict)
                    else getattr(link, "block_id", None)
                    for link in block_links
                    if (
                        link.get("block_id")
                        if isinstance(link, dict)
                        else getattr(link, "block_id", None)
                    )
                ]

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
            payload["is_full"] = bool(payload.get("waitlist", False)) or (
                confirmed >= (payload.get("capacity", 0) or 0)
            )

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
    blocks: list[UUID] | None = None

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
                self.day_of_week,
                self.capacity,
                self.description,
                self.photo_album_url,
                self.internal_notes,
                self.archived,
                self.blocks,
            ]
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SessionEmail(CamelizedBaseSchema):
    subject: str
    message: str
