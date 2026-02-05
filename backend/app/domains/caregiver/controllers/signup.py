from __future__ import annotations

import logging
import uuid

from litestar import Controller, delete, get, post
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ValidationException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domains.caregiver.schemas.signup import (
    SignupCreateRequest,
    SignupCreateResponse,
    SignupFull,
)
from app.domains.caregiver.services.caregiver import CaregiverService
from app.domains.caregiver.services.auth import AuthSessionService
from app.domains.caregiver.guards import get_current_caregiver
from app.domains.caregiver.services.signup import SignupService
from app.domains.caregiver.services.student import StudentService
from app.lib.age import is_age_eligible as check_age_eligible
from app.lib.auth import utcnow
from app.lib.deps import get_task_queue
from app.domains.public.services.session import SessionService as PublicSessionService
from advanced_alchemy.extensions.litestar import providers

logger = logging.getLogger(__name__)


class SignupController(Controller):
    """Caregiver signup endpoints for managing session enrollments."""

    path = "/api/v1/signups"
    tags = ["Caregiver Signups"]
    dependencies = providers.create_service_dependencies(
        SignupService,
        "signup_service",
    )
    dependencies.update(
        providers.create_service_dependencies(
            StudentService,
            "student_service",
        )
    )
    dependencies.update(
        providers.create_service_dependencies(
            PublicSessionService,
            "session_service",
        )
    )
    dependencies.update(
        providers.create_service_dependencies(
            CaregiverService,
            "caregiver_service",
        )
    )
    dependencies.update(
        providers.create_service_dependencies(
            AuthSessionService,
            "auth_session_service",
        )
    )
    dependencies.update(
        {
            "current_caregiver": Provide(get_current_caregiver),
        }
    )

    @get("/", status_code=HTTP_200_OK, summary="List caregiver signups")
    async def list_signups(
        self,
        signup_service: SignupService,
        current_caregiver: m.Caregiver,
    ) -> list[SignupFull]:
        """List all signups for the current caregiver with eager loading."""
        # Eager load relationships to avoid N+1 queries
        caregiver_students = select(m.Student.id).where(
            m.Student.caregiver_id == current_caregiver.id
        )
        signups = await signup_service.list(
            m.Signup.student_id.in_(caregiver_students),
            load=[
                selectinload(m.Signup.student),
                selectinload(m.Signup.session).selectinload(m.Session.location),
            ],
        )

        results = []
        for signup in signups:
            results.append(
                SignupFull(
                    id=signup.id,
                    status=signup.status,  # type: ignore[arg-type]
                    created_at=signup.created_at,
                    withdrawn_at=signup.withdrawn_at,
                    pickup_dropoff=signup.pickup_dropoff,
                    needs_devices=signup.needs_devices,
                    session_id=signup.session_id,
                    session_name=signup.session.name,
                    student_id=signup.student_id,
                    student_name=signup.student.name,
                )
            )

        return results

    @post(
        "/{session_id:uuid}", status_code=HTTP_201_CREATED, summary="Signup to session"
    )
    async def create_signup(
        self,
        session_id: uuid.UUID,
        data: SignupCreateRequest,
        signup_service: SignupService,
        student_service: StudentService,
        session_service: PublicSessionService,
        caregiver_service: CaregiverService,
        current_caregiver: m.Caregiver,
    ) -> SignupCreateResponse:
        """Create a signup for the caregiver's student to a session.

        Prevents duplicate signups and automatically determines status based on:
        - Student age eligibility
        - Session capacity
        - Session waitlist status

        Queues a confirmation email to the caregiver.
        """
        # Verify caregiver profile is complete
        if not current_caregiver.name or not current_caregiver.phone:
            raise ValidationException(
                detail="Complete your profile before signing up. Name and phone number are required."
            )

        # Get the session
        session = await session_service.get(session_id)
        if not session:
            raise NotFoundException(detail="Session not found")

        # Validate and get the student
        try:
            student_uuid = uuid.UUID(data.student_id)
        except (ValueError, AttributeError):
            raise ValidationException(detail="Invalid student ID format")

        student = await student_service.get(student_uuid)
        if not student or student.caregiver_id != current_caregiver.id:
            raise NotFoundException(detail="Student not found or doesn't belong to you")

        # Verify student has required information
        if not student.date_of_birth:
            raise ValidationException(
                detail="Student date of birth is required before signing up"
            )

        # Check age eligibility
        is_age_eligible, age_reason = check_age_eligible(
            student.date_of_birth,
            session.age_lower,
            session.age_upper,
        )

        # Check for existing signup
        existing_signups = await signup_service.list(
            m.Signup.session_id == session_id,
            m.Signup.student_id == student_uuid,
        )

        if existing_signups:
            existing = existing_signups[0]
            if existing.status != "withdrawn":
                raise ValidationException(
                    detail=f"Student is already signed up with status: {existing.status}"
                )

            # Re-activate withdrawn signup with pending status
            await signup_service.update(
                {
                    "status": "pending",
                    "withdrawn_at": None,
                    "pickup_dropoff": data.pickup_dropoff,
                    "needs_devices": data.needs_devices,
                },
                existing.id,
            )
            logger.info(
                f"Re-activated signup {existing.id} for student {student_uuid} to session {session_id} with pending status"
            )

            # Queue background task to process signup
            try:
                queue = await get_task_queue()
                await queue.enqueue(
                    "process_signup_approval_task",
                    signup_id=str(existing.id),
                    caregiver_id=str(current_caregiver.id),
                    student_id=str(student_uuid),
                    session_id=str(session_id),
                )
                logger.info(f"Queued signup processing task for signup {existing.id}")
            except Exception as e:
                logger.error(f"Failed to queue signup processing task: {e}")

            return SignupCreateResponse(id=str(existing.id), status="pending")

        # Create new signup with pending status (will be processed by background task)
        new_signup = await signup_service.create(
            {
                "session_id": session_id,
                "student_id": student_uuid,
                "status": "pending",
                "pickup_dropoff": data.pickup_dropoff,
                "needs_devices": data.needs_devices,
            }
        )
        logger.info(
            f"Created pending signup {new_signup.id} for student {student_uuid} to session {session_id}"
        )

        # Queue background task to process signup
        try:
            queue = await get_task_queue()
            await queue.enqueue(
                "process_signup_approval_task",
                signup_id=str(new_signup.id),
                caregiver_id=str(current_caregiver.id),
                student_id=str(student_uuid),
                session_id=str(session_id),
            )
            logger.info(f"Queued signup processing task for signup {new_signup.id}")
        except Exception as e:
            logger.error(f"Failed to queue signup processing task: {e}")
            # Don't raise - signup creation should succeed even if task queueing fails

        return SignupCreateResponse(id=str(new_signup.id), status="pending")

    @delete("/{signup_id:uuid}", status_code=HTTP_200_OK, summary="Withdraw signup")
    async def withdraw_signup(
        self,
        signup_id: uuid.UUID,
        signup_service: SignupService,
        current_caregiver: m.Caregiver,
    ) -> dict:
        """Withdraw an existing signup.

        When a signup is withdrawn:
        - Status is set to "withdrawn"
        - A cancellation confirmation email is sent
        - If the student was confirmed, the next waitlisted student can be promoted

        Args:
            signup_id: ID of the signup to withdraw
            signup_service: Service for signup operations
            current_caregiver: The authenticated caregiver

        Returns:
            Success message

        Raises:
            NotFoundException: If signup not found or doesn't belong to caregiver
        """
        signup = await signup_service.get(
            signup_id,
            load=[selectinload(m.Signup.student), selectinload(m.Signup.session)],
        )
        if not signup or signup.student.caregiver_id != current_caregiver.id:
            raise NotFoundException(detail="Signup not found")

        if signup.status == "withdrawn":
            return {"message": "Signup already withdrawn"}

        # Update status
        await signup_service.update(
            {
                "status": "withdrawn",
                "withdrawn_at": utcnow(),
            },
            signup_id,
        )
        logger.info(f"Withdrew signup {signup_id}")

        # Queue cancellation email
        try:
            queue = await get_task_queue()
            await queue.enqueue(
                "send_signup_cancelled_task",
                signup_id=str(signup_id),
                to_email=current_caregiver.email,
                caregiver_name=current_caregiver.name or "Caregiver",
                student_name=signup.student.name,
                session_name=signup.session.name,
                cancellation_reason="Withdrawn by caregiver",
            )
            logger.info(f"Queued cancellation email for signup {signup_id}")
        except Exception as e:
            logger.error(f"Failed to queue cancellation email: {e}")

        return {"message": "Signup withdrawn successfully"}


async def _queue_confirmation_email(
    caregiver: m.Caregiver,
    student: m.Student,
    session: m.Session,
    signup_id: uuid.UUID,
    status: str,
    waitlist_reason: str | None = None,
) -> None:
    """Queue a signup confirmation email using the SAQ worker.

    Sends appropriate email template based on confirmation status:
    - confirmed: immediate confirmation with session details
    - waitlist ed: waitlist notification with reason why on waitlist
    - pending: pending approval notification

    Args:
        caregiver: The caregiver making the signup
        student: The student being signed up
        session: The session being signed up for
        signup_id: ID of the signup record
        status: Status of the signup (confirmed/waitlisted/pending)
        waitlist_reason: Reason why student is waitlisted (if applicable)
    """
    try:
        queue = await get_task_queue()
        session_location = session.location.name if session.location else "TBD"
        session_address = session.location.address if session.location else ""

        await queue.enqueue(
            "send_signup_confirmation_task",
            to_email=caregiver.email,
            caregiver_name=caregiver.name or "Caregiver",
            student_name=student.name,
            session_name=session.name,
            session_venue=session_location,
            session_address=session_address,
            status=status,
            signup_id=str(signup_id),
            waitlist_reason=waitlist_reason,
        )
        logger.info(f"Queued {status} confirmation email for signup {signup_id}")
    except Exception as e:
        logger.error(f"Failed to queue confirmation email: {e}")
        # Don't raise - email queueing failure shouldn't block the signup
