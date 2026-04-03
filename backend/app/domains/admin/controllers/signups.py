from __future__ import annotations

import datetime
import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers
from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError
from litestar import Controller, get, patch, post
from litestar.exceptions import NotFoundException
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.signup import (
    Signup,
    SignupCreate,
    SignupStatus,
    SignupStatusUpdate,
    SignupStudent,
    SignupUpdate,
)
from app.domains.admin.services.signup import SignupService
from app.lib.deps import get_task_queue
from app.lib.session_time import format_session_time

logger = logging.getLogger(__name__)


class SignupController(Controller):
    """Admin endpoints for managing signups."""

    path = "/api/v1/admin/signups"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        SignupService,
        "signup_service",
        # Default loading strategy - load student and session relationships
        load=[
            selectinload(m.Signup.student).selectinload(m.Student.caregiver),
            selectinload(m.Signup.session).selectinload(m.Session.location),
        ],
    )

    @get("/{signup_id:uuid}")
    async def get_signup(
        self,
        signup_id: UUID,
        signup_service: SignupService,
    ) -> SignupStudent:
        """Get a single signup by ID."""
        try:
            signup = await signup_service.get(signup_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Signup not found")
        if not signup:
            raise NotFoundException(detail="Signup not found")
        return signup_service.to_schema(signup, schema_type=SignupStudent)

    @post("/")
    async def create_signup(
        self,
        data: SignupCreate,
        signup_service: SignupService,
    ) -> Signup:
        """Create a new signup."""
        signup = await signup_service.create(data)
        # Refresh to load relationships (student, student.caregiver)
        try:
            signup = await signup_service.get(signup.id)
        except AlchemyNotFoundError:
            pass  # Use the created object if refresh fails
        return signup_service.to_schema(signup, schema_type=Signup)

    @patch("/{signup_id:uuid}")
    async def update_signup(
        self,
        signup_id: UUID,
        data: SignupUpdate,
        signup_service: SignupService,
    ) -> SignupStudent:
        """Update an existing signup."""
        signup_data = data.model_dump(exclude_unset=True)
        if data.status == SignupStatus.WITHDRAWN:
            signup_data["withdrawn_at"] = datetime.datetime.now(datetime.timezone.utc)

        try:
            signup = await signup_service.update(signup_data, signup_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Signup not found")
        if not signup:
            raise NotFoundException(detail="Signup not found")
        if not signup:
            raise NotFoundException(detail="Signup not found")
        return signup_service.to_schema(signup, schema_type=SignupStudent)

    @patch("/{signup_id:uuid}/status")
    async def update_signup_status(
        self,
        signup_id: UUID,
        data: SignupStatusUpdate,
        signup_service: SignupService,
    ) -> SignupStudent:
        """Update the status of a signup.

        Allows admins to manually override signup status, for example to move
        someone from waitlist to confirmed or vice versa. Optionally notifies
        the caregiver and records a reason for the change.
        """
        # Get the signup (will use default load options from controller dependencies)
        try:
            signup = await signup_service.get(signup_id)
        except AlchemyNotFoundError:
            raise NotFoundException(detail="Signup not found")
        if not signup:
            raise NotFoundException(detail="Signup not found")

        old_status = signup.status
        signup_data = {"status": data.status}

        # If changing to withdrawn, set withdrawn_at timestamp
        if data.status == SignupStatus.WITHDRAWN:
            signup_data["withdrawn_at"] = datetime.datetime.now(datetime.timezone.utc)
        # If changing from withdrawn to something else, clear withdrawn_at
        else:
            if signup.withdrawn_at:
                signup_data["withdrawn_at"] = None

        signup = await signup_service.update(signup_data, signup_id)

        # Queue notification email if requested
        if data.notify_caregiver:
            try:
                queue = await get_task_queue()
                caregiver = signup.student.caregiver
                session = signup.session
                session_time = format_session_time(session)

                # Determine email type based on status change
                if data.status == SignupStatus.CONFIRMED:
                    await queue.enqueue(
                        "send_waitlist_promoted_task",
                        signup_id=str(signup_id),
                        to_email=caregiver.email,
                        caregiver_name=caregiver.name or "Caregiver",
                        student_name=signup.student.name,
                        session_name=session.name,
                        session_venue=session.location.name if session.location else "",
                        session_address=session.location.address
                        if session.location
                        else "",
                        session_time=session_time,
                        session_id=str(session.id),
                    )
                    logger.info(
                        f"Queued waitlist promotion email for signup {signup_id}"
                    )
                elif data.status == SignupStatus.WITHDRAWN:
                    reason = data.reason or "Withdrawn by administrator"
                    await queue.enqueue(
                        "send_signup_cancelled_task",
                        signup_id=str(signup_id),
                        to_email=caregiver.email,
                        caregiver_name=caregiver.name or "Caregiver",
                        student_name=signup.student.name,
                        session_name=session.name,
                        cancellation_reason=reason,
                    )
                    logger.info(f"Queued cancellation email for signup {signup_id}")
                elif (
                    data.status == SignupStatus.WAITLISTED
                    and old_status == SignupStatus.CONFIRMED
                ):
                    # Notifying of demotion from confirmed to waitlist
                    await queue.enqueue(
                        "send_signup_confirmation_task",
                        signup_id=str(signup_id),
                        to_email=caregiver.email,
                        caregiver_name=caregiver.name or "Caregiver",
                        student_name=signup.student.name,
                        session_name=session.name,
                        session_venue=session.location.name if session.location else "",
                        session_address=session.location.address
                        if session.location
                        else "",
                        session_time=session_time,
                        signup_status="waitlisted",
                        waitlist_reason=data.reason,
                        session_id=str(session.id),
                    )
                    logger.info(
                        f"Queued waitlist demotion email for signup {signup_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to queue notification email: {e}")

        return signup_service.to_schema(signup, schema_type=SignupStudent)
