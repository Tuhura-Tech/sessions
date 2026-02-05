from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, model_validator

from app.lib.schema import CamelizedBaseSchema


class StaffPublic(CamelizedBaseSchema):
    """Public staff schema without sensitive SSO information."""

    id: UUID
    name: str
    email: EmailStr
    active: bool
    last_login_at: datetime | None = None


class Staff(CamelizedBaseSchema):
    """Full staff schema including SSO ID for detailed views."""

    id: UUID
    name: str
    email: EmailStr
    sso_id: str
    active: bool
    last_login_at: datetime | None = None
    deactivated_at: datetime | None = None


class StaffCreate(CamelizedBaseSchema):
    name: str
    email: EmailStr
    sso_id: str


class StaffUpdate(CamelizedBaseSchema):
    name: str | None = None
    email: EmailStr | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(v is None for v in [self.name, self.email, self.active]):
            raise ValueError("At least one field must be provided for update.")
        return self


class StaffSessionSummary(CamelizedBaseSchema):
    """Summary of a session for staff listing."""

    id: UUID
    name: str
    year: int
    session_type: str
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    location_name: str | None = None


class SessionStaffAssignment(CamelizedBaseSchema):
    """Information about a staff assignment to a session."""

    id: UUID
    staff_id: UUID
    session_id: UUID
    assigned_at: datetime


class StaffAssignmentCreate(CamelizedBaseSchema):
    """Assign a single staff member to a session."""

    staff_id: UUID


class BulkStaffAssignment(CamelizedBaseSchema):
    """Bulk assign staff to a session."""

    staff_ids: list[UUID]
    replace: bool = False  # If True, replace all existing assignments


class StaffAvailability(CamelizedBaseSchema):
    """Staff availability and capacity information."""

    staff_id: UUID
    name: str
    email: EmailStr
    active: bool
    assigned_session_count: int
    session_ids: list[UUID]
