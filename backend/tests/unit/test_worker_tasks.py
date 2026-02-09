"""Tests for worker task execution with mocked dependencies.

Each worker task is tested for:
- Successful execution path
- Error handling / failure path
- Correct return value structure

All external I/O is mocked:
- ``email_service`` (render_template, send) via app.lib.email.email_service
- ``_get_db_session`` (async DB session) via app.lib.worker._get_db_session
- ``notify_newsletter_subscription`` via app.lib.newsletter
- ``get_task_queue`` (SAQ queue for process_session_reminders_task)
- SAQ ``ctx["queue"]`` (enqueue)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.lib.worker import (
    bulk_promote_waitlist_task,
    bulk_withdraw_signups_task,
    notify_newsletter_subscription_task,
    process_session_reminders_task,
    process_signup_approval_task,
    send_caregiver_message_task,
    send_occurrence_cancelled_task,
    send_session_cancelled_task,
    send_session_reminder_task,
    send_signup_cancelled_task,
    send_signup_confirmation_task,
    send_waitlist_promoted_task,
)

pytestmark = [pytest.mark.anyio, pytest.mark.unit]

tz = ZoneInfo("Pacific/Auckland")

# The email_service singleton is imported inside each task function body as:
#   from app.lib.email import email_service
# so we must patch the canonical location: "app.lib.email.email_service"
EMAIL_SVC = "app.lib.email.email_service"

# _get_db_session is a module-level function used by DB tasks
DB_SESSION = "app.lib.worker._get_db_session"


def _make_ctx(queue: AsyncMock | None = None) -> dict[str, Any]:
    """Create a minimal SAQ-like context dict."""
    if queue is None:
        queue = AsyncMock()
    return {"queue": queue}


# ============================================================================
# send_signup_confirmation_task
# ============================================================================


class TestSendSignupConfirmationTask:
    """Tests for send_signup_confirmation_task."""

    @patch(EMAIL_SVC)
    async def test_confirmed_status(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>confirmed</html>", "confirmed text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_signup_confirmation_task(
            _make_ctx(),
            to_email="parent@example.com",
            caregiver_name="Jane Doe",
            student_name="Kid One",
            session_name="Robotics",
            session_venue="Lab",
            session_address="123 Test St",
            signup_status="confirmed",
            signup_id="abc-123",
            session_id="session-123",
        )

        assert result["success"] is True
        assert result["to_email"] == "parent@example.com"
        assert result["signup_id"] == "abc-123"
        assert result["signup_status"] == "confirmed"
        assert "sent_at" in result

        mock_email.render_template.assert_awaited_once()
        call_args = mock_email.render_template.call_args
        assert call_args[0][0] == "signup_confirmation_confirmed"

    @patch(EMAIL_SVC)
    async def test_waitlisted_status(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>waitlisted</html>", "waitlisted text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_signup_confirmation_task(
            _make_ctx(),
            to_email="parent@example.com",
            caregiver_name="Jane",
            student_name="Kid",
            session_name="Art",
            session_venue="Studio",
            session_address="456 Art Ln",
            signup_status="waitlisted",
            signup_id="def-456",
            waitlist_reason="session full",
            session_id="session-456",
        )

        assert result["success"] is True
        call_args = mock_email.render_template.call_args
        assert call_args[0][0] == "signup_confirmation_waitlisted"

    @patch(EMAIL_SVC)
    async def test_pending_status(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>pending</html>", "pending text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_signup_confirmation_task(
            _make_ctx(),
            to_email="parent@example.com",
            caregiver_name="Jane",
            student_name="Kid",
            session_name="Art",
            session_venue="Studio",
            session_address="456 Art Ln",
            signup_status="pending",
            signup_id="ghi-789",
            session_id="session-789",
        )

        assert result["success"] is True
        call_args = mock_email.render_template.call_args
        assert call_args[0][0] == "signup_confirmation_pending"

    @patch(EMAIL_SVC)
    async def test_email_send_failure(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(return_value="<html></html>")
        mock_email.send = AsyncMock(return_value=False)

        result = await send_signup_confirmation_task(
            _make_ctx(),
            to_email="parent@example.com",
            caregiver_name="Jane",
            student_name="Kid",
            session_name="Art",
            session_venue="Studio",
            session_address="456 Art Ln",
            signup_status="confirmed",
            signup_id="fail-1",
            session_id="session-fail",
        )

        assert result["success"] is False

    @patch(EMAIL_SVC)
    async def test_exception_returns_error(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(side_effect=RuntimeError("boom"))

        result = await send_signup_confirmation_task(
            _make_ctx(),
            to_email="x@x.com",
            caregiver_name="N",
            student_name="S",
            session_name="Ses",
            session_venue="V",
            session_address="A",
            signup_status="confirmed",
            signup_id="err-1",
            session_id="session-err",
        )

        assert result["success"] is False
        assert "error" in result
        assert "boom" in result["error"]


# ============================================================================
# send_waitlist_promoted_task
# ============================================================================


class TestSendWaitlistPromotedTask:
    """Tests for send_waitlist_promoted_task."""

    @patch(EMAIL_SVC)
    async def test_success(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>promoted</html>", "promoted text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_waitlist_promoted_task(
            _make_ctx(),
            signup_id="su-1",
            to_email="carer@example.com",
            caregiver_name="Alice",
            student_name="Bob",
            session_name="Coding",
            session_venue="Lab A",
            session_address="1 Tech Rd",
            session_id="session-1",
        )

        assert result["success"] is True
        assert result["signup_id"] == "su-1"
        assert result["to_email"] == "carer@example.com"
        assert "sent_at" in result

    @patch(EMAIL_SVC)
    async def test_exception_returns_error(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(side_effect=Exception("send failed"))

        result = await send_waitlist_promoted_task(
            _make_ctx(),
            signup_id="su-2",
            to_email="x@x.com",
            caregiver_name="N",
            student_name="S",
            session_name="Ses",
            session_venue="V",
            session_address="A",
            session_id="session-2",
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# send_signup_cancelled_task
# ============================================================================


class TestSendSignupCancelledTask:
    """Tests for send_signup_cancelled_task."""

    @patch(EMAIL_SVC)
    async def test_success_with_reason(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>cancelled</html>", "cancelled text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_signup_cancelled_task(
            _make_ctx(),
            signup_id="c-1",
            to_email="carer@example.com",
            caregiver_name="Alice",
            student_name="Bob",
            session_name="Science",
            cancellation_reason="No longer available",
        )

        assert result["success"] is True
        assert result["signup_id"] == "c-1"
        assert "sent_at" in result

    @patch(EMAIL_SVC)
    async def test_success_without_reason(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>cancelled</html>", "cancelled text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_signup_cancelled_task(
            _make_ctx(),
            signup_id="c-2",
            to_email="carer@example.com",
            caregiver_name="Alice",
            student_name="Bob",
            session_name="Science",
        )

        assert result["success"] is True

    @patch(EMAIL_SVC)
    async def test_exception_returns_error(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(side_effect=RuntimeError("fail"))

        result = await send_signup_cancelled_task(
            _make_ctx(),
            signup_id="c-3",
            to_email="x@x.com",
            caregiver_name="N",
            student_name="S",
            session_name="X",
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# send_caregiver_message_task
# ============================================================================


class TestSendCaregiverMessageTask:
    """Tests for send_caregiver_message_task."""

    @patch(EMAIL_SVC)
    async def test_success(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>msg</html>", "plain text msg")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_caregiver_message_task(
            _make_ctx(),
            to_email="carer@example.com",
            caregiver_name="Alice",
            subject="Hello",
            message="Body text",
        )

        assert result["success"] is True
        assert result["to_email"] == "carer@example.com"
        assert "sent_at" in result

    @patch(EMAIL_SVC)
    async def test_exception_returns_error(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(side_effect=Exception("template error"))

        result = await send_caregiver_message_task(
            _make_ctx(),
            to_email="carer@example.com",
            caregiver_name="Alice",
            subject="Test",
            message="Body",
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# send_session_cancelled_task
# ============================================================================


class TestSendSessionCancelledTask:
    """Tests for send_session_cancelled_task."""

    @patch(DB_SESSION)
    @patch(EMAIL_SVC)
    async def test_sends_to_all_confirmed_signups(
        self, mock_email: MagicMock, mock_get_db: AsyncMock
    ) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>cancelled</html>", "cancelled text")
        )
        mock_email.send = AsyncMock(return_value=True)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("a@example.com", "Alice", "Kid A"),
                    ("b@example.com", "Bob", "Kid B"),
                ]
            )
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await send_session_cancelled_task(
            _make_ctx(),
            session_id="sess-1",
            session_name="Robotics",
            cancellation_date="2026-03-01",
            cancellation_reason="Weather",
        )

        assert result["success"] is True
        assert result["emails_sent"] == 2
        assert result["emails_failed"] == 0
        assert mock_email.send.await_count == 2
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    @patch(EMAIL_SVC)
    async def test_partial_failure(
        self, mock_email: MagicMock, mock_get_db: AsyncMock
    ) -> None:
        mock_email.render_template = AsyncMock(return_value=("<html></html>", "text"))
        mock_email.send = AsyncMock(side_effect=[True, False])

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("a@example.com", "Alice", "Kid A"),
                    ("b@example.com", "Bob", "Kid B"),
                ]
            )
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await send_session_cancelled_task(
            _make_ctx(),
            session_id="sess-2",
            session_name="Art",
            cancellation_date="2026-04-01",
        )

        assert result["success"] is False
        assert result["emails_sent"] == 1
        assert result["emails_failed"] == 1

    @patch(DB_SESSION)
    async def test_db_error(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("db down"))
        mock_get_db.return_value = mock_db

        result = await send_session_cancelled_task(
            _make_ctx(),
            session_id="sess-3",
            session_name="X",
            cancellation_date="2026-01-01",
        )

        assert result["success"] is False
        assert "error" in result
        mock_db.close.assert_awaited_once()


# ============================================================================
# send_occurrence_cancelled_task
# ============================================================================


class TestSendOccurrenceCancelledTask:
    """Tests for send_occurrence_cancelled_task."""

    @patch(DB_SESSION)
    @patch(EMAIL_SVC)
    async def test_sends_to_all_confirmed(
        self, mock_email: MagicMock, mock_get_db: AsyncMock
    ) -> None:
        mock_email.render_template = AsyncMock(return_value=("<html></html>", "text"))
        mock_email.send = AsyncMock(return_value=True)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("c@example.com", "Carol", "Kid C"),
                ]
            )
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await send_occurrence_cancelled_task(
            _make_ctx(),
            occurrence_id="occ-1",
            session_id="sess-1",
            session_name="Coding",
            occurrence_date="2026-05-01",
            cancellation_reason="Room unavailable",
        )

        assert result["success"] is True
        assert result["occurrence_id"] == "occ-1"
        assert result["emails_sent"] == 1
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_db_error(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
        mock_get_db.return_value = mock_db

        result = await send_occurrence_cancelled_task(
            _make_ctx(),
            occurrence_id="occ-2",
            session_id="sess-2",
            session_name="X",
            occurrence_date="2026-06-01",
        )

        assert result["success"] is False
        assert "error" in result
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    @patch(EMAIL_SVC)
    async def test_no_signups(
        self, mock_email: MagicMock, mock_get_db: AsyncMock
    ) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await send_occurrence_cancelled_task(
            _make_ctx(),
            occurrence_id="occ-3",
            session_id="sess-3",
            session_name="Empty",
            occurrence_date="2026-07-01",
        )

        assert result["success"] is True
        assert result["emails_sent"] == 0
        mock_email.send.assert_not_called()


# ============================================================================
# process_signup_approval_task
# ============================================================================


class TestProcessSignupApprovalTask:
    """Tests for process_signup_approval_task."""

    def _build_mock_db(
        self,
        signup: Any = None,
        student: Any = None,
        session: Any = None,
        caregiver: Any = None,
    ) -> AsyncMock:
        """Build a mock DB session with get() returning objects by model type."""
        mock_db = AsyncMock()

        async def mock_get(model: type, id: str) -> Any:  # noqa: A002
            from app.db import models as m

            if model is m.Signup:
                return signup
            if model is m.Student:
                return student
            if model is m.Session:
                return session
            if model is m.Caregiver:
                return caregiver
            return None

        mock_db.get = AsyncMock(side_effect=mock_get)
        mock_db.merge = AsyncMock()
        mock_db.commit = AsyncMock()
        return mock_db

    @patch(DB_SESSION)
    async def test_signup_not_found(self, mock_get_db: AsyncMock) -> None:
        mock_db = self._build_mock_db(signup=None)
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="missing",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="se-1",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_student_not_found(self, mock_get_db: AsyncMock) -> None:
        mock_signup = MagicMock()
        mock_db = self._build_mock_db(signup=mock_signup, student=None)
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="su-1",
            caregiver_id="cg-1",
            student_id="missing",
            session_id="se-1",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch(DB_SESSION)
    async def test_session_not_found(self, mock_get_db: AsyncMock) -> None:
        mock_signup = MagicMock()
        mock_student = MagicMock()
        mock_db = self._build_mock_db(
            signup=mock_signup, student=mock_student, session=None
        )
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="su-1",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="missing",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch(DB_SESSION)
    async def test_confirmed_when_eligible_and_space(
        self, mock_get_db: AsyncMock
    ) -> None:
        from datetime import date, timedelta

        mock_signup = MagicMock()
        mock_signup.status = "pending"
        mock_student = MagicMock()
        mock_student.date_of_birth = date.today() - timedelta(days=365 * 10)
        mock_student.name = "Test Kid"
        mock_session = MagicMock()
        mock_session.age_lower = 5
        mock_session.age_upper = 15
        mock_session.is_full = False
        mock_session.name = "Science"
        mock_session.location = MagicMock()
        mock_session.location.name = "Lab"
        mock_session.location.address = "1 St"
        mock_caregiver = MagicMock()
        mock_caregiver.email = "carer@example.com"
        mock_caregiver.name = "Carer"

        mock_db = self._build_mock_db(
            signup=mock_signup,
            student=mock_student,
            session=mock_session,
            caregiver=mock_caregiver,
        )
        mock_get_db.return_value = mock_db

        queue_mock = AsyncMock()
        result = await process_signup_approval_task(
            _make_ctx(queue=queue_mock),
            signup_id="su-ok",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="se-1",
        )

        assert result["success"] is True
        assert result["final_status"] == "confirmed"
        assert result["age_eligible"] is True
        assert mock_signup.status == "confirmed"
        mock_db.merge.assert_awaited_once()
        mock_db.commit.assert_awaited_once()
        queue_mock.enqueue.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_waitlisted_when_eligible_but_full(
        self, mock_get_db: AsyncMock
    ) -> None:
        from datetime import date, timedelta

        mock_signup = MagicMock()
        mock_signup.status = "pending"
        mock_student = MagicMock()
        mock_student.date_of_birth = date.today() - timedelta(days=365 * 10)
        mock_student.name = "Kid"
        mock_session = MagicMock()
        mock_session.age_lower = 5
        mock_session.age_upper = 15
        mock_session.is_full = True
        mock_session.name = "Full Session"
        mock_session.location = MagicMock()
        mock_session.location.name = "Room"
        mock_session.location.address = "2 St"
        mock_caregiver = MagicMock()
        mock_caregiver.email = "carer@test.com"
        mock_caregiver.name = "Carer"

        mock_db = self._build_mock_db(
            signup=mock_signup,
            student=mock_student,
            session=mock_session,
            caregiver=mock_caregiver,
        )
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="su-full",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="se-1",
        )

        assert result["success"] is True
        assert result["final_status"] == "waitlisted"
        assert mock_signup.status == "waitlisted"

    @patch(DB_SESSION)
    async def test_pending_when_age_ineligible(self, mock_get_db: AsyncMock) -> None:
        from datetime import date, timedelta

        mock_signup = MagicMock()
        mock_signup.status = "pending"
        mock_student = MagicMock()
        mock_student.date_of_birth = date.today() - timedelta(days=365 * 3)
        mock_student.name = "Young Kid"
        mock_session = MagicMock()
        mock_session.age_lower = 8
        mock_session.age_upper = 15
        mock_session.is_full = False
        mock_session.name = "Advanced"
        mock_session.location = None
        mock_caregiver = MagicMock()
        mock_caregiver.email = "c@test.com"
        mock_caregiver.name = "C"

        mock_db = self._build_mock_db(
            signup=mock_signup,
            student=mock_student,
            session=mock_session,
            caregiver=mock_caregiver,
        )
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="su-young",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="se-1",
        )

        assert result["success"] is True
        assert result["final_status"] == "pending"
        assert result["age_eligible"] is False

    @patch(DB_SESSION)
    async def test_no_dob_keeps_pending(self, mock_get_db: AsyncMock) -> None:
        mock_signup = MagicMock()
        mock_signup.status = "pending"
        mock_student = MagicMock()
        mock_student.date_of_birth = None
        mock_student.name = "No DOB"
        mock_session = MagicMock()
        mock_session.age_lower = 5
        mock_session.age_upper = 15
        mock_session.is_full = False
        mock_session.name = "Session"
        mock_session.location = None
        mock_caregiver = MagicMock()
        mock_caregiver.email = "c@test.com"
        mock_caregiver.name = "C"

        mock_db = self._build_mock_db(
            signup=mock_signup,
            student=mock_student,
            session=mock_session,
            caregiver=mock_caregiver,
        )
        mock_get_db.return_value = mock_db

        result = await process_signup_approval_task(
            _make_ctx(),
            signup_id="su-nodob",
            caregiver_id="cg-1",
            student_id="st-1",
            session_id="se-1",
        )

        assert result["success"] is True
        assert result["final_status"] == "pending"
        assert result["age_eligible"] is False


# ============================================================================
# bulk_promote_waitlist_task
# ============================================================================


class TestBulkPromoteWaitlistTask:
    """Tests for bulk_promote_waitlist_task."""

    @patch(DB_SESSION)
    async def test_session_not_found(self, mock_get_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await bulk_promote_waitlist_task(
            _make_ctx(), session_id="missing", count=5
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_no_capacity(self, mock_get_db: AsyncMock) -> None:
        mock_session = MagicMock()
        mock_session.capacity = 2
        confirmed_1 = MagicMock()
        confirmed_1.status = "confirmed"
        confirmed_2 = MagicMock()
        confirmed_2.status = "confirmed"
        mock_session.signups = [confirmed_1, confirmed_2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await bulk_promote_waitlist_task(
            _make_ctx(), session_id="full-sess", count=3
        )

        assert result["success"] is False
        assert result["promoted"] == 0
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_promotes_waitlisted_signups(self, mock_get_db: AsyncMock) -> None:
        from datetime import timezone

        mock_session = MagicMock()
        mock_session.capacity = 5
        mock_session.name = "Fun Session"
        mock_session.location = MagicMock()
        mock_session.location.name = "Lab"
        mock_session.location.address = "1 St"

        confirmed = MagicMock()
        confirmed.status = "confirmed"

        waitlisted_1 = MagicMock()
        waitlisted_1.status = "waitlisted"
        waitlisted_1.id = "w1"
        waitlisted_1.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        waitlisted_1.student = MagicMock()
        waitlisted_1.student.name = "Kid W1"
        waitlisted_1.student.caregiver = MagicMock()
        waitlisted_1.student.caregiver.email = "w1@test.com"
        waitlisted_1.student.caregiver.name = "Parent W1"

        waitlisted_2 = MagicMock()
        waitlisted_2.status = "waitlisted"
        waitlisted_2.id = "w2"
        waitlisted_2.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        waitlisted_2.student = MagicMock()
        waitlisted_2.student.name = "Kid W2"
        waitlisted_2.student.caregiver = MagicMock()
        waitlisted_2.student.caregiver.email = "w2@test.com"
        waitlisted_2.student.caregiver.name = "Parent W2"

        mock_session.signups = [confirmed, waitlisted_1, waitlisted_2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session)
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        queue_mock = AsyncMock()
        result = await bulk_promote_waitlist_task(
            _make_ctx(queue=queue_mock), session_id="sess-p", count=10
        )

        assert result["success"] is True
        assert result["promoted"] == 2
        assert result["failed"] == 0
        assert waitlisted_1.status == "confirmed"
        assert waitlisted_2.status == "confirmed"
        assert queue_mock.enqueue.await_count == 2
        mock_db.commit.assert_awaited_once()
        mock_db.close.assert_awaited_once()


# ============================================================================
# bulk_withdraw_signups_task
# ============================================================================


class TestBulkWithdrawSignupsTask:
    """Tests for bulk_withdraw_signups_task."""

    @patch(DB_SESSION)
    async def test_withdraws_all_signups(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("su-1", "a@test.com", "Alice", "Kid A"),
                    ("su-2", "b@test.com", "Bob", "Kid B"),
                ]
            )
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_signup_1 = MagicMock()
        mock_signup_2 = MagicMock()
        mock_db.get = AsyncMock(side_effect=[mock_signup_1, mock_signup_2])
        mock_get_db.return_value = mock_db

        queue_mock = AsyncMock()
        result = await bulk_withdraw_signups_task(
            _make_ctx(queue=queue_mock),
            session_id="sess-w",
            reason="Session cancelled",
        )

        assert result["success"] is True
        assert result["withdrawn"] == 2
        assert mock_signup_1.status == "withdrawn"
        assert mock_signup_2.status == "withdrawn"
        assert queue_mock.enqueue.await_count == 2
        mock_db.commit.assert_awaited_once()
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_no_signups_to_withdraw(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await bulk_withdraw_signups_task(
            _make_ctx(), session_id="empty-sess", reason="test"
        )

        assert result["success"] is True
        assert result["withdrawn"] == 0

    @patch(DB_SESSION)
    async def test_db_error(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("db error"))
        mock_get_db.return_value = mock_db

        result = await bulk_withdraw_signups_task(
            _make_ctx(), session_id="err-sess", reason="test"
        )

        assert result["success"] is False
        assert "error" in result
        mock_db.close.assert_awaited_once()


# ============================================================================
# send_session_reminder_task
# ============================================================================


class TestSendSessionReminderTask:
    """Tests for send_session_reminder_task."""

    @patch(EMAIL_SVC)
    async def test_success(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>reminder</html>", "reminder text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_session_reminder_task(
            _make_ctx(),
            signup_id="rem-1",
            to_email="carer@test.com",
            caregiver_name="Carer",
            student_name="Kid",
            session_name="Art",
            occurrence_date="2026-03-15",
            days_until=7,
        )

        assert result["success"] is True
        assert result["signup_id"] == "rem-1"
        assert result["days_until"] == 7
        assert "sent_at" in result

    @patch(EMAIL_SVC)
    async def test_1_day_reminder(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(
            return_value=("<html>reminder</html>", "reminder text")
        )
        mock_email.send = AsyncMock(return_value=True)

        result = await send_session_reminder_task(
            _make_ctx(),
            signup_id="rem-2",
            to_email="carer@test.com",
            caregiver_name="Carer",
            student_name="Kid",
            session_name="Art",
            occurrence_date="2026-03-08",
            days_until=1,
        )

        assert result["success"] is True
        assert result["days_until"] == 1

    @patch(EMAIL_SVC)
    async def test_exception_returns_error(self, mock_email: MagicMock) -> None:
        mock_email.render_template = AsyncMock(side_effect=Exception("template fail"))

        result = await send_session_reminder_task(
            _make_ctx(),
            signup_id="rem-err",
            to_email="x@test.com",
            caregiver_name="N",
            student_name="S",
            session_name="Ses",
            occurrence_date="2026-01-01",
            days_until=7,
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# process_session_reminders_task
# ============================================================================


class TestProcessSessionRemindersTask:
    """Tests for process_session_reminders_task (daily cronjob)."""

    @patch(DB_SESSION)
    async def test_no_upcoming_sessions(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        result = await process_session_reminders_task(_make_ctx())

        assert result["success"] is True
        assert result["reminders_queued"] == 0
        mock_db.close.assert_awaited_once()

    @patch(DB_SESSION)
    async def test_db_error(self, mock_get_db: AsyncMock) -> None:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("connection reset"))
        mock_get_db.return_value = mock_db

        result = await process_session_reminders_task(_make_ctx())

        assert result["success"] is False
        assert "error" in result
        mock_db.close.assert_awaited_once()

    @patch("app.lib.deps.get_task_queue", new_callable=AsyncMock)
    @patch(DB_SESSION)
    async def test_queues_reminders_for_matching_days(
        self, mock_get_db: AsyncMock, mock_get_queue: AsyncMock
    ) -> None:
        """Test that reminders are queued for occurrences 7 days away."""
        from datetime import timedelta

        today = datetime.now(tz).date()
        seven_days_away = today + timedelta(days=7)

        mock_row = MagicMock()
        mock_row.id = "signup-1"
        mock_row.student_id = "student-1"
        mock_row.session_id = "session-1"
        mock_row.occurrence_id = "occ-1"
        mock_row.starts_at = datetime.combine(
            seven_days_away, datetime.min.time(), tzinfo=tz
        )
        mock_row.student_name = "Kid"
        mock_row.caregiver_name = "Carer"
        mock_row.caregiver_email = "carer@test.com"
        mock_row.session_name = "Science"
        mock_row.occurrence_rank = 1

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db

        mock_queue = AsyncMock()
        mock_get_queue.return_value = mock_queue

        result = await process_session_reminders_task(_make_ctx())

        assert result["success"] is True
        assert result["reminders_queued"] == 1
        mock_queue.enqueue.assert_awaited_once()
        mock_db.close.assert_awaited_once()


# ============================================================================
# notify_newsletter_subscription_task
# ============================================================================


class TestNotifyNewsletterSubscriptionTask:
    """Tests for notify_newsletter_subscription_task."""

    @patch("app.lib.newsletter.notify_newsletter_subscription", new_callable=AsyncMock)
    async def test_success(self, mock_notify: AsyncMock) -> None:
        mock_notify.return_value = True

        result = await notify_newsletter_subscription_task(
            _make_ctx(),
            email="subscriber@test.com",
            name="Subscriber",
        )

        assert result["success"] is True
        assert result["email"] == "subscriber@test.com"
        assert "sent_at" in result
        mock_notify.assert_awaited_once_with(
            email="subscriber@test.com", name="Subscriber"
        )

    @patch("app.lib.newsletter.notify_newsletter_subscription", new_callable=AsyncMock)
    async def test_exception_returns_error(self, mock_notify: AsyncMock) -> None:
        mock_notify.side_effect = Exception("webhook failed")

        result = await notify_newsletter_subscription_task(
            _make_ctx(),
            email="fail@test.com",
            name="Fail",
        )

        assert result["success"] is False
        assert "error" in result
        assert "webhook failed" in result["error"]
