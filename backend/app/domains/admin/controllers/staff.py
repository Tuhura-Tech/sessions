from __future__ import annotations

import datetime
import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers
from litestar import Controller, get, patch, post
from litestar import delete as http_delete
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ValidationException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.staff import (
    BulkStaffAssignment,
    SessionStaffAssignment,
    Staff,
    StaffAssignmentCreate,
    StaffAvailability,
    StaffCreate,
    StaffPublic,
    StaffSessionSummary,
    StaffUpdate,
)
from app.domains.admin.services.session import SessionService
from app.domains.admin.services.staff import SessionStaffService, StaffService

logger = logging.getLogger(__name__)


class StaffController(Controller):
    """Admin endpoints for managing staff."""

    path = "/api/v1/admin/staff"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = {
        "staff_service": Provide(providers.create_service_provider(StaffService)),
        "session_staff_service": Provide(
            providers.create_service_provider(SessionStaffService)
        ),
        "session_service": Provide(providers.create_service_provider(SessionService)),
    }

    @get("/")
    async def list_staff(
        self,
        staff_service: StaffService,
        active_only: bool = True,
    ) -> list[StaffPublic]:
        """List all staff members.

        Returns public staff information without internal authentication identifiers.
        """
        filters = {}
        if active_only:
            filters["active"] = True

        results = await staff_service.list(**filters)
        return [
            staff_service.to_schema(staff, schema_type=StaffPublic) for staff in results
        ]

    @get("/{staff_id:uuid}")
    async def get_staff(
        self,
        staff_id: UUID,
        staff_service: StaffService,
    ) -> Staff:
        """Get a single staff member by ID."""
        staff = await staff_service.get(staff_id)
        if not staff:
            raise NotFoundException(detail="Staff not found")
        return staff_service.to_schema(staff, schema_type=Staff)

    @post("/")
    async def create_staff(
        self,
        data: StaffCreate,
        staff_service: StaffService,
    ) -> Staff:
        """Create a new staff member.

        This is typically called after SSO authentication to create
        a staff record in the database.
        """
        # Check if staff with this email or sso_id already exists
        existing = await staff_service.list(email=data.email)
        if existing:
            raise ValidationException(
                detail="Staff member with this email already exists"
            )

        existing_sso = await staff_service.list(sso_id=data.sso_id)
        if existing_sso:
            raise ValidationException(
                detail="Staff member with this SSO ID already exists"
            )

        staff = await staff_service.create(
            {
                "name": data.name,
                "email": data.email,
                "sso_id": data.sso_id,
                "active": True,
                "last_login_at": datetime.datetime.now(datetime.timezone.utc),
            }
        )
        return staff_service.to_schema(staff, schema_type=Staff)

    @patch("/{staff_id:uuid}")
    async def update_staff(
        self,
        staff_id: UUID,
        data: StaffUpdate,
        staff_service: StaffService,
        session_staff_service: SessionStaffService,
        session_service: SessionService,
    ) -> Staff:
        """Update a staff member's details.

        When deactivating staff, automatically removes them from all future session assignments.
        """
        staff_data = data.model_dump(exclude_unset=True)

        # If deactivating, set deactivated_at and remove from future sessions
        if "active" in staff_data and not staff_data["active"]:
            staff_data["deactivated_at"] = datetime.datetime.now(datetime.timezone.utc)

            # Remove from future sessions (sessions that haven't started yet)
            assignments = await session_staff_service.list(
                staff_id=staff_id, load=[selectinload(m.SessionStaff.session)]
            )

            now = datetime.datetime.now(datetime.timezone.utc)
            for assignment in assignments:
                # Get session start time from first occurrence
                occurrences = await session_service.occurrences.list(
                    session_id=assignment.session_id,
                    limit=1,
                )
                if occurrences and occurrences[0].starts_at > now:
                    # Session hasn't started yet, remove assignment
                    await session_staff_service.delete(assignment.id)

        elif "active" in staff_data and staff_data["active"]:
            staff_data["deactivated_at"] = None

        staff = await staff_service.update(staff_data, staff_id)
        if not staff:
            raise NotFoundException(detail="Staff not found")

        return staff_service.to_schema(staff, schema_type=Staff)

    @get("/{staff_id:uuid}/sessions")
    async def get_staff_sessions(
        self,
        staff_id: UUID,
        staff_service: StaffService,
        session_staff_service: SessionStaffService,
    ) -> list[StaffSessionSummary]:
        """Get all sessions assigned to a staff member."""
        # Verify staff exists
        staff = await staff_service.get(staff_id)
        if not staff:
            raise NotFoundException(detail="Staff not found")

        # Get all session assignments
        assignments = await session_staff_service.list(
            staff_id=staff_id,
            load=[
                selectinload(m.SessionStaff.session).selectinload(m.Session.location),
            ],
        )

        return [
            StaffSessionSummary(
                id=assignment.session.id,
                name=assignment.session.name,
                year=assignment.session.year,
                session_type=assignment.session.session_type,
                day_of_week=assignment.session.day_of_week,
                start_time=str(assignment.session.start_time),
                end_time=str(assignment.session.end_time),
                location_name=assignment.session.location.name if assignment.session.location else None,
            )
            for assignment in assignments
        ]

    @get("/availability")
    async def get_staff_availability(
        self,
        staff_service: StaffService,
        session_staff_service: SessionStaffService,
        year: int | None = None,
        active_only: bool = True,
    ) -> list[StaffAvailability]:
        """Get staff workload and availability information.

        Returns each staff member with their assigned session counts, grouped by year
        for capacity planning and workload distribution analysis.
        """
        filters = {}
        if active_only:
            filters["active"] = True

        all_staff = await staff_service.list(**filters)

        availability = []
        for staff in all_staff:
            # Get session assignments
            assignments = await session_staff_service.list(
                staff_id=staff.id, load=[selectinload(m.SessionStaff.session)]
            )

            # Filter by year if specified
            if year:
                assignments = [a for a in assignments if a.session.year == year]

            availability.append(
                StaffAvailability(
                    staff_id=staff.id,
                    name=staff.name,
                    email=staff.email,
                    active=staff.active,
                    assigned_session_count=len(assignments),
                    session_ids=[a.session_id for a in assignments],
                )
            )

        return availability


class SessionStaffController(Controller):
    """Admin endpoints for managing staff assignments to sessions."""

    path = "/api/v1/admin/sessions/{session_id:uuid}/staff"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = {
        "session_service": Provide(providers.create_service_provider(SessionService)),
        "staff_service": Provide(providers.create_service_provider(StaffService)),
        "session_staff_service": Provide(
            providers.create_service_provider(SessionStaffService)
        ),
    }

    @get("/")
    async def get_session_staff(
        self,
        session_id: UUID,
        session_service: SessionService,
        session_staff_service: SessionStaffService,
    ) -> list[StaffPublic]:
        """Get all staff assigned to a session.

        Returns public staff information without internal authentication identifiers.
        """
        # Get all staff assignments
        assignments = await session_staff_service.list(
            session_id=session_id,
            load=[selectinload(m.SessionStaff.staff)],
        )

        return [
            StaffPublic(
                id=assignment.staff.id,
                name=assignment.staff.name,
                email=assignment.staff.email,
                active=assignment.staff.active,
                last_login_at=assignment.staff.last_login_at,
            )
            for assignment in assignments
        ]

    @post("/")
    async def assign_staff(
        self,
        session_id: UUID,
        data: StaffAssignmentCreate,
        session_service: SessionService,
        staff_service: StaffService,
        session_staff_service: SessionStaffService,
    ) -> SessionStaffAssignment:
        """Assign a staff member to a session.

        Uses database constraints to prevent duplicate assignments and race conditions.
        """
        # Let database constraint handle duplicate prevention
        try:
            assignment = await session_staff_service.create(
                {
                    "session_id": session_id,
                    "staff_id": data.staff_id,
                }
            )
        except IntegrityError as e:
            error_str = str(e)
            if "uq_session_staff" in error_str:
                raise ValidationException(
                    detail="Staff member is already assigned to this session"
                )
            elif "fk_session_staff_session_id" in error_str:
                raise NotFoundException(detail="Session not found")
            elif "fk_session_staff_staff_id" in error_str:
                raise NotFoundException(detail="Staff member not found")
            raise

        return SessionStaffAssignment(
            id=assignment.id,
            staff_id=assignment.staff_id,
            session_id=assignment.session_id,
            assigned_at=assignment.assigned_at,
        )

    @http_delete("/{staff_id:uuid}")
    async def remove_staff(
        self,
        session_id: UUID,
        staff_id: UUID,
        session_staff_service: SessionStaffService,
    ) -> None:
        """Remove a staff member from a session."""
        # Find the assignment
        assignments = await session_staff_service.list(
            session_id=session_id, staff_id=staff_id
        )

        if not assignments:
            raise NotFoundException(detail="Staff assignment not found")

        # Delete the assignment
        await session_staff_service.delete(assignments[0].id)

        return None

    #             existing.last_login_at = datetime.now()
    #             # Update name/email in case they changed in SSO
    #             exist

    @post("/bulk")
    async def bulk_assign_staff(
        self,
        session_id: UUID,
        data: BulkStaffAssignment,
        session_staff_service: SessionStaffService,
    ) -> list[SessionStaffAssignment]:
        """Assign multiple staff members to a session in a single transaction.

        If replace=True, removes all existing staff assignments before adding new ones.

        """
        if data.replace:
            # Remove all existing assignments
            existing = await session_staff_service.list(session_id=session_id)
            for assignment in existing:
                await session_staff_service.delete(assignment.id)

        results = []
        for staff_id in data.staff_ids:
            try:
                assignment = await session_staff_service.create(
                    {
                        "session_id": session_id,
                        "staff_id": staff_id,
                    }
                )
                results.append(
                    SessionStaffAssignment(
                        id=assignment.id,
                        staff_id=assignment.staff_id,
                        session_id=assignment.session_id,
                        assigned_at=assignment.assigned_at,
                    )
                )
            except IntegrityError as e:
                # Skip duplicates if not in replace mode
                if "uq_session_staff" not in str(e):
                    raise

        return results
