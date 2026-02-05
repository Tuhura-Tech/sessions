"""Background worker tasks for SAQ queue processing.

This module contains all background job handlers for async operations:
- Email notifications (signups, waitlist updates, cancellations)
- Batch email processing (scheduled daily)
- Attendee status transitions and notifications
- Bulk operations on signups/attendance
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from saq.types import Context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.lib.age import calculate_age, is_age_eligible
from app.lib.settings import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
tz = ZoneInfo("Pacific/Auckland")


async def _get_db_session() -> AsyncSession:
    """Get a new database session for worker tasks."""
    from app.lib.settings import _get_sqlalchemy_settings

    sqlalchemy_config = _get_sqlalchemy_settings()
    engine = sqlalchemy_config.engine_instance
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return session_maker()


# ============================================================================
# EMAIL NOTIFICATION TASKS
# ============================================================================


async def send_signup_confirmation_task(
    ctx: Context,
    *,
    to_email: str,
    caregiver_name: str,
    student_name: str,
    session_name: str,
    session_venue: str,
    session_address: str,
    status: str,
    signup_id: str,
    waitlist_reason: str | None = None,
) -> dict[str, Any]:
    """Send signup confirmation email when a student signs up for a session.

    Args:
        ctx: SAQ context
        to_email: Caregiver email address
        caregiver_name: Name of the caregiver
        student_name: Name of the student
        session_name: Name of the session
        session_venue: Venue name
        session_address: Venue address
        status: Signup status (confirmed/waitlisted/pending)
        signup_id: ID of the signup record
        waitlist_reason: Reason why student is on waitlist (if applicable)

    Returns:
        Dictionary with task result metadata
    """
    logger.info(f"Sending signup confirmation to {to_email} for signup {signup_id}")

    try:
        from app.lib.email import email_service

        # Compose email content based on status
        if status == "confirmed":
            subject = f"✓ Confirmed: {student_name} - {session_name}"
            template = "signup_confirmation_confirmed"
        elif status == "waitlisted":
            subject = f"📋 Waitlisted: {student_name} - {session_name}"
            template = "signup_confirmation_waitlisted"
        else:
            subject = f"📌 Pending: {student_name} - {session_name}"
            template = "signup_confirmation_pending"

        # Render and send email
        html = await email_service.render_template(
            f"{template}.html",
            caregiver_name=caregiver_name,
            student_name=student_name,
            session_name=session_name,
            session_venue=session_venue,
            session_address=session_address,
            status=status,
            waitlist_reason=waitlist_reason,
            support_email=settings.email_contact,
        )

        message = {
            "to": [to_email],
            "subject": subject,
            "html": html,
            "from": settings.email_from,
        }

        # Send via email service
        success = await email_service.send(message)

        return {
            "success": success,
            "to_email": to_email,
            "signup_id": signup_id,
            "status": status,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to send signup confirmation: {e}", exc_info=True)
        return {
            "success": False,
            "to_email": to_email,
            "signup_id": signup_id,
            "error": str(e),
        }


async def send_waitlist_promoted_task(
    ctx: Context,
    *,
    signup_id: str,
    to_email: str,
    caregiver_name: str,
    student_name: str,
    session_name: str,
    session_venue: str,
    session_address: str,
) -> dict[str, Any]:
    """Send email when a student is promoted from waitlist to confirmed.

    This task is queued when an admin or system promotes a waitlisted signup.

    Args:
        ctx: SAQ context
        signup_id: ID of the signup record
        to_email: Caregiver email address
        caregiver_name: Name of the caregiver
        student_name: Name of the student
        session_name: Name of the session
        session_venue: Venue name
        session_address: Venue address

    Returns:
        Dictionary with task result metadata
    """
    logger.info(
        f"Sending waitlist promotion email to {to_email} for signup {signup_id}"
    )

    try:
        from app.lib.email import email_service

        subject = f"🎉 Spot confirmed: {student_name} - {session_name}"

        html = await email_service.render_template(
            "waitlist_promoted.html",
            caregiver_name=caregiver_name,
            student_name=student_name,
            session_name=session_name,
            session_venue=session_venue,
            session_address=session_address,
            support_email=settings.email_contact,
        )

        message = {
            "to": [to_email],
            "subject": subject,
            "html": html,
            "from": settings.email_from,
        }

        success = await email_service.send(message)

        return {
            "success": success,
            "signup_id": signup_id,
            "to_email": to_email,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to send waitlist promotion email: {e}", exc_info=True)
        return {
            "success": False,
            "signup_id": signup_id,
            "error": str(e),
        }


async def send_signup_cancelled_task(
    ctx: Context,
    *,
    signup_id: str,
    to_email: str,
    caregiver_name: str,
    student_name: str,
    session_name: str,
    cancellation_reason: str | None = None,
) -> dict[str, Any]:
    """Send email when a signup is cancelled (by caregiver or admin).

    Args:
        ctx: SAQ context
        signup_id: ID of the signup record
        to_email: Caregiver email address
        caregiver_name: Name of the caregiver
        student_name: Name of the student
        session_name: Name of the session
        cancellation_reason: Optional reason for cancellation

    Returns:
        Dictionary with task result metadata
    """
    logger.info(f"Sending cancellation email to {to_email} for signup {signup_id}")

    try:
        from app.lib.email import email_service

        subject = f"Cancelled: {student_name} - {session_name}"

        html = await email_service.render_template(
            "signup_cancelled.html",
            caregiver_name=caregiver_name,
            student_name=student_name,
            session_name=session_name,
            cancellation_reason=cancellation_reason,
            support_email=settings.email_contact,
        )

        message = {
            "to": [to_email],
            "subject": subject,
            "html": html,
            "from": settings.email_from,
        }

        success = await email_service.send(message)

        return {
            "success": success,
            "signup_id": signup_id,
            "to_email": to_email,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}", exc_info=True)
        return {
            "success": False,
            "signup_id": signup_id,
            "error": str(e),
        }


async def send_caregiver_message_task(
    ctx: Context,
    *,
    to_email: str,
    caregiver_name: str,
    subject: str,
    message: str,
) -> dict[str, Any]:
    """Send a direct message to a caregiver.

    Args:
        ctx: SAQ context
        to_email: Caregiver email address
        caregiver_name: Name of the caregiver
        subject: Email subject
        message: Email body (plain text)

    Returns:
        Dictionary with task result metadata
    """
    logger.info("Sending caregiver message to %s", to_email)

    try:
        from app.lib.email import email_service

        html, text = await email_service.render_template(
            "caregiver_message",
            caregiver_name=caregiver_name,
            subject=subject,
            message=message,
            support_email=settings.email_contact,
        )

        email = {
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
            "from": settings.email_from,
        }

        success = await email_service.send(email)

        return {
            "success": success,
            "to_email": to_email,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error("Failed to send caregiver message: %s", e, exc_info=True)
        return {
            "success": False,
            "to_email": to_email,
            "error": str(e),
        }


async def send_session_cancelled_task(
    ctx: Context,
    *,
    session_id: str,
    session_name: str,
    cancellation_date: str,
    cancellation_reason: str | None = None,
) -> dict[str, Any]:
    """Send bulk email to all confirmed signups when a session is cancelled.

    Args:
        ctx: SAQ context
        session_id: ID of the session
        session_name: Name of the session
        cancellation_date: Date of cancellation (ISO format)
        cancellation_reason: Optional reason for cancellation

    Returns:
        Dictionary with task result metadata (number of emails sent)
    """
    logger.info(f"Sending session cancellation notices for session {session_id}")

    db = await _get_db_session()
    emails_sent = 0
    emails_failed = 0

    try:
        from app.lib.email import email_service

        # Get all confirmed signups for this session
        result = await db.execute(
            text(
                f"""
                SELECT DISTINCT c.email, c.name, s.name
                FROM {m.Signup.__tablename__} su
                JOIN {m.Caregiver.__tablename__} c ON su.caregiver_id = c.id
                JOIN {m.Student.__tablename__} s ON su.student_id = s.id
                WHERE su.session_id = :session_id AND su.status = 'confirmed'
                """
            ),
            {"session_id": session_id},
        )

        for to_email, caregiver_name, student_name in result:
            try:
                subject = f"🚫 Cancelled: {student_name} - {session_name}"

                html = await email_service.render_template(
                    "session_cancelled.html",
                    caregiver_name=caregiver_name,
                    student_name=student_name,
                    session_name=session_name,
                    cancellation_date=cancellation_date,
                    cancellation_reason=cancellation_reason,
                    support_email=settings.email_contact,
                )

                message = {
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "from": settings.email_from,
                }

                success = await email_service.send(message)
                if success:
                    emails_sent += 1
                else:
                    emails_failed += 1
            except Exception as e:
                logger.error(f"Failed to send cancellation email to {to_email}: {e}")
                emails_failed += 1

        return {
            "success": emails_failed == 0,
            "session_id": session_id,
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to process session cancellation: {e}", exc_info=True)
        return {
            "success": False,
            "session_id": session_id,
            "error": str(e),
        }
    finally:
        await db.close()


async def send_occurrence_cancelled_task(
    ctx: Context,
    *,
    occurrence_id: str,
    session_id: str,
    session_name: str,
    occurrence_date: str,
    cancellation_reason: str | None = None,
) -> dict[str, Any]:
    """Send email to caregivers when a single occurrence is cancelled.

    Args:
        ctx: SAQ context
        occurrence_id: ID of the cancelled occurrence
        session_id: ID of the session
        session_name: Name of the session
        occurrence_date: Date of the cancelled occurrence (ISO format)
        cancellation_reason: Optional reason for cancellation

    Returns:
        Dictionary with task result metadata
    """
    logger.info(
        f"Sending occurrence cancellation notices for occurrence {occurrence_id}"
    )

    db = await _get_db_session()
    emails_sent = 0

    try:
        from app.lib.email import email_service

        # Get all confirmed signups for this session
        result = await db.execute(
            text(
                f"""
                SELECT DISTINCT c.email, c.name, s.name
                FROM {m.Signup.__tablename__} su
                JOIN {m.Caregiver.__tablename__} c ON su.caregiver_id = c.id
                JOIN {m.Student.__tablename__} s ON su.student_id = s.id
                WHERE su.session_id = :session_id AND su.status = 'confirmed'
                """
            ),
            {"session_id": session_id},
        )

        for to_email, caregiver_name, student_name in result:
            try:
                subject = f"⚠️ Session moved: {student_name} - {session_name}"

                html = await email_service.render_template(
                    "occurrence_cancelled.html",
                    caregiver_name=caregiver_name,
                    student_name=student_name,
                    session_name=session_name,
                    occurrence_date=occurrence_date,
                    cancellation_reason=cancellation_reason,
                    support_email=settings.email_contact,
                )

                message = {
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "from": settings.email_from,
                }

                if await email_service.send(message):
                    emails_sent += 1
            except Exception as e:
                logger.error(
                    f"Failed to send occurrence cancellation email to {to_email}: {e}"
                )

        return {
            "success": True,
            "occurrence_id": occurrence_id,
            "emails_sent": emails_sent,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to process occurrence cancellation: {e}", exc_info=True)
        return {
            "success": False,
            "occurrence_id": occurrence_id,
            "error": str(e),
        }
    finally:
        await db.close()


# ============================================================================
# SIGNUP APPROVAL PROCESSING
# ============================================================================


async def process_signup_approval_task(
    ctx: Context,
    *,
    signup_id: str,
    caregiver_id: str,
    student_id: str,
    session_id: str,
) -> dict[str, Any]:
    """Process a pending signup to determine final status based on age and capacity.

    This task is queued when a new signup is created. It determines whether the
    signup should be confirmed, waitlisted, or remain pending for staff review.

    Logic:
    - If student is age-eligible AND session has space → confirm
    - If student is age-eligible AND session is full → waitlist
    - If student is NOT age-eligible → keep pending (needs staff review)

    Args:
        ctx: SAQ context
        signup_id: ID of the signup record
        caregiver_id: ID of the caregiver
        student_id: ID of the student
        session_id: ID of the session

    Returns:
        Dictionary with task result metadata
    """
    logger.info(f"Processing approval for signup {signup_id}")

    db = await _get_db_session()

    try:
        # Fetch signup, student, session from database
        signup = await db.get(m.Signup, signup_id)
        if not signup:
            logger.warning(f"Signup {signup_id} not found")
            return {
                "success": False,
                "signup_id": signup_id,
                "error": "Signup not found",
            }

        student = await db.get(m.Student, student_id)
        if not student:
            logger.warning(f"Student {student_id} not found")
            return {
                "success": False,
                "signup_id": signup_id,
                "error": "Student not found",
            }

        session = await db.get(m.Session, session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return {
                "success": False,
                "signup_id": signup_id,
                "error": "Session not found",
            }

        # Calculate student age and check eligibility
        dob = student.date_of_birth
        if dob:
            age = calculate_age(dob)
            age_eligible, age_ineligible_reason = is_age_eligible(
                dob,
                session.age_lower,
                session.age_upper,
            )
        else:
            # No DOB - treat as ineligible for age filtering
            age = None
            age_eligible = False
            age_ineligible_reason = "Date of birth required for age verification"

        # Determine final status
        final_status = None
        caregiver = await db.get(m.Caregiver, caregiver_id)
        waitlist_reason = None

        if not age_eligible:
            # Out of age range - keep pending for staff review
            final_status = "pending"
            logger.info(
                f"Signup {signup_id} kept pending (age ineligible): {age_ineligible_reason}"
            )
        elif session.is_full:
            # Age eligible but no space - waitlist
            final_status = "waitlisted"
            waitlist_reason = "session is at capacity"
            logger.info(f"Signup {signup_id} waitlisted: {waitlist_reason}")
        else:
            # Age eligible and space available - confirm
            final_status = "confirmed"
            logger.info(f"Signup {signup_id} confirmed")

        # Update signup status in database
        signup.status = final_status
        await db.merge(signup)
        await db.commit()

        # Queue appropriate notification email
        if caregiver and caregiver.email:
            await ctx["queue"].enqueue(
                "send_signup_confirmation_task",
                to_email=caregiver.email,
                caregiver_name=caregiver.name,
                student_name=student.name,
                session_name=session.name,
                session_venue=session.location.name if session.location else "TBD",
                session_address=session.location.address if session.location else "TBD",
                status=final_status,
                signup_id=signup_id,
                waitlist_reason=waitlist_reason
                if final_status == "waitlisted"
                else None,
            )

        return {
            "success": True,
            "signup_id": signup_id,
            "final_status": final_status,
            "age_eligible": age_eligible,
            "student_age": age,
            "processed_at": datetime.now(tz).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to process signup approval: {e}", exc_info=True)
        return {
            "success": False,
            "signup_id": signup_id,
            "error": str(e),
        }
    finally:
        await db.close()


# ============================================================================
# BULK OPERATIONS
# ============================================================================


async def bulk_promote_waitlist_task(
    ctx: Context,
    *,
    session_id: str,
    count: int,
) -> dict[str, Any]:
    """Promote waitlisted signups to confirmed when space opens up.

    This task handles the logic of:
    1. Checking available capacity
    2. Promoting waitlisted signups in order
    3. Sending promotion emails to caregivers

    Args:
        ctx: SAQ context
        session_id: ID of the session
        count: Number of students to promote (default: all available capacity)

    Returns:
        Dictionary with promotion results
    """
    logger.info(f"Promoting {count} waitlisted signups for session {session_id}")

    db = await _get_db_session()
    promoted = 0
    failed = 0

    try:
        # Get session details
        session = await db.get(m.Session, session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        # Get available capacity
        confirmed_count = sum(1 for s in session.signups if s.status == "confirmed")
        available = session.capacity - confirmed_count

        if available <= 0:
            return {
                "success": False,
                "promoted": 0,
                "error": "No available capacity",
            }

        # Promote waitlisted signups
        promote_limit = min(count, available)
        waitlisted = [s for s in session.signups if s.status == "waitlisted"]
        waitlisted = sorted(waitlisted, key=lambda s: s.created_at)[:promote_limit]

        for signup in waitlisted:
            try:
                # Update signup status
                signup.status = "confirmed"
                db.add(signup)
                await db.flush()

                # Queue promotion email
                caregiver = signup.student.caregiver
                if caregiver and caregiver.email:
                    await ctx["queue"].enqueue(
                        "send_waitlist_promoted_task",
                        signup_id=str(signup.id),
                        to_email=caregiver.email,
                        caregiver_name=caregiver.name or "Caregiver",
                        student_name=signup.student.name,
                        session_name=session.name,
                        session_venue=session.location.name
                        if session.location
                        else "TBD",
                        session_address=session.location.address
                        if session.location
                        else "",
                    )
                    promoted += 1
            except Exception as e:
                logger.error(f"Failed to promote signup {signup.id}: {e}")
                failed += 1

        await db.commit()

        return {
            "success": failed == 0,
            "session_id": session_id,
            "promoted": promoted,
            "failed": failed,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to process bulk promotion: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }
    finally:
        await db.close()


async def bulk_withdraw_signups_task(
    ctx: Context,
    *,
    session_id: str,
    reason: str = "Session cancelled",
) -> dict[str, Any]:
    """Withdraw all signups for a session and notify caregivers.

    Args:
        ctx: SAQ context
        session_id: ID of the session
        reason: Reason for withdrawal

    Returns:
        Dictionary with withdrawal results
    """
    logger.info(f"Withdrawing all signups for session {session_id}")

    db = await _get_db_session()
    withdrawn = 0

    try:
        # Get all non-withdrawn signups
        result = await db.execute(
            text(f"""
            SELECT su.id, c.email, c.name, s.name
            FROM {m.Signup.__tablename__} su
            JOIN {m.Caregiver.__tablename__} c ON su.caregiver_id = c.id
            JOIN {m.Student.__tablename__} s ON su.student_id = s.id
            WHERE su.session_id = :session_id AND su.status != 'withdrawn'
            """),
            {"session_id": session_id},
        )

        now = datetime.now(tz)

        for signup_id, to_email, caregiver_name, student_name in result:
            try:
                # Update signup
                signup = await db.get(m.Signup, signup_id)
                if signup:
                    signup.status = "withdrawn"
                    signup.withdrawn_at = now
                    db.add(signup)

                    # Queue cancellation email
                    if to_email:
                        await ctx["queue"].enqueue(
                            "send_signup_cancelled_task",
                            signup_id=str(signup_id),
                            to_email=to_email,
                            caregiver_name=caregiver_name,
                            student_name=student_name,
                            session_name="",
                            cancellation_reason=reason,
                        )

                    withdrawn += 1
            except Exception as e:
                logger.error(f"Failed to withdraw signup {signup_id}: {e}")

        await db.commit()

        return {
            "success": True,
            "session_id": session_id,
            "withdrawn": withdrawn,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to process bulk withdrawal: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }
    finally:
        await db.close()


# ============================================================================
# SESSION REMINDERS (Scheduled)
# ============================================================================


async def send_session_reminder_task(
    ctx: Context,
    *,
    signup_id: str,
    to_email: str,
    caregiver_name: str,
    student_name: str,
    session_name: str,
    occurrence_date: str,
    days_until: int,
) -> dict[str, Any]:
    """Send a reminder notification for an upcoming session.

    Args:
        ctx: SAQ context
        signup_id: The signup ID
        to_email: Caregiver email address
        caregiver_name: Caregiver name for personalization
        student_name: Student name
        session_name: Session name
        occurrence_date: ISO format date of the occurrence
        days_until: Number of days until the session

    Returns:
        Dictionary with send result
    """
    logger.info(
        f"Sending {days_until}-day reminder for signup {signup_id} to {to_email}"
    )

    try:
        from app.lib.email import email_service

        context = {
            "caregiver_name": caregiver_name,
            "student_name": student_name,
            "session_name": session_name,
            "occurrence_date": occurrence_date,
            "days_until": days_until,
            "portal_url": settings.PORTAL_URL,
            "support_email": f"mailto:{settings.SUPPORT_EMAIL}",
        }

        html = await email_service.render_template(
            "session_reminder.html", context=context
        )
        await email_service.send(
            {
                "to": [to_email],
                "subject": f"Reminder: {session_name} in {days_until} day{'s' if days_until != 1 else ''}",
                "html": html,
            }
        )

        return {
            "success": True,
            "signup_id": signup_id,
            "to_email": to_email,
            "days_until": days_until,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(
            f"Failed to send reminder for signup {signup_id}: {e}", exc_info=True
        )
        return {
            "success": False,
            "signup_id": signup_id,
            "error": str(e),
        }


async def process_session_reminders_task(
    ctx: Context,
) -> dict[str, Any]:
    """Daily cronjob to send session reminders.

    Sends reminders 7 days and 1 day before the first occurrence of each
    session that a caregiver has signed up for.

    This task should be scheduled to run once daily via cronjob.

    Returns:
        Dictionary with processing results
    """
    logger.info("Starting daily session reminder processing")

    try:
        from sqlalchemy import and_, func, select

        db = await _get_db_session()

        # Get today's date in NZ timezone
        today = datetime.now(tz).date()

        # Find occurrences that are exactly 7 or 1 day away
        # Filter to only confirmed signups
        # Only process the first occurrence per session per signup
        query = (
            select(
                m.Signup.id,
                m.Signup.student_id,
                m.Signup.session_id,
                m.Occurrence.id.label("occurrence_id"),
                m.Occurrence.starts_at,
                m.Student.name.label("student_name"),
                m.Caregiver.name.label("caregiver_name"),
                m.Caregiver.email.label("caregiver_email"),
                m.Session.name.label("session_name"),
                func.row_number()
                .over(
                    partition_by=(m.Signup.session_id, m.Signup.student_id),
                    order_by=m.Occurrence.starts_at,
                )
                .label("occurrence_rank"),
            )
            .join(m.Signup.student)
            .join(m.Student.caregiver)
            .join(m.Signup.session)
            .join(m.Session.occurrences)
            .where(
                and_(
                    m.Signup.status == "confirmed",
                    ~m.Occurrence.cancelled,
                    m.Occurrence.starts_at.is_not(None),
                )
            )
        )

        results = await db.execute(query)
        all_signups = results.fetchall()

        # Filter to first occurrence and calculate days until
        reminders_queued = 0

        for row in all_signups:
            # Only process the first occurrence per signup
            if row.occurrence_rank != 1:
                continue

            occurrence_date = row.starts_at.date()
            days_until = (occurrence_date - today).days

            # Send reminders for 7 days and 1 day before
            if days_until in (7, 1):
                logger.info(
                    f"Queueing {days_until}-day reminder for signup {row.id} "
                    f"({row.student_name} - {row.session_name})"
                )

                # Queue the reminder task
                from app.lib.deps import get_task_queue

                queue = await get_task_queue()
                await queue.enqueue(
                    "send_session_reminder_task",
                    signup_id=str(row.id),
                    to_email=row.caregiver_email,
                    caregiver_name=row.caregiver_name or "Caregiver",
                    student_name=row.student_name,
                    session_name=row.session_name,
                    occurrence_date=occurrence_date.isoformat(),
                    days_until=days_until,
                )
                reminders_queued += 1

        logger.info(
            f"Session reminder processing complete. "
            f"Queued {reminders_queued} reminders."
        )

        return {
            "success": True,
            "reminders_processed": len(all_signups),
            "reminders_queued": reminders_queued,
            "processed_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to process session reminders: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }
    finally:
        await db.close()


# ============================================================================
# NEWSLETTER & COMMUNICATIONS
# ============================================================================


async def notify_newsletter_subscription_task(
    ctx: Context,
    *,
    email: str,
    name: str,
) -> dict[str, Any]:
    """Notify external newsletter service of new subscription.

    Args:
        ctx: SAQ context
        email: Email address to subscribe
        name: Name of the subscriber

    Returns:
        Dictionary with notification result
    """
    logger.info(f"Notifying newsletter of new subscription: {email}")

    try:
        from app.lib.newsletter import notify_newsletter_subscription

        success = await notify_newsletter_subscription(email=email, name=name)

        return {
            "success": success,
            "email": email,
            "sent_at": datetime.now(tz).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to notify newsletter: {e}", exc_info=True)
        return {
            "success": False,
            "email": email,
            "error": str(e),
        }


__all__ = [
    "send_signup_confirmation_task",
    "send_waitlist_promoted_task",
    "send_signup_cancelled_task",
    "send_caregiver_message_task",
    "send_session_cancelled_task",
    "send_occurrence_cancelled_task",
    "bulk_promote_waitlist_task",
    "bulk_withdraw_signups_task",
    "send_session_reminder_task",
    "process_session_reminders_task",
    "notify_newsletter_subscription_task",
]
