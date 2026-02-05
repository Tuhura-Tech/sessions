"""Tests for worker module structure and basic functionality."""

from __future__ import annotations

import pytest

# Test that worker tasks can be imported
from app.lib.worker import (
    send_signup_confirmation_task,
    send_waitlist_promoted_task,
    send_signup_cancelled_task,
    send_caregiver_message_task,
    send_session_cancelled_task,
    send_occurrence_cancelled_task,
    process_signup_approval_task,
    bulk_promote_waitlist_task,
    bulk_withdraw_signups_task,
    send_session_reminder_task,
    process_session_reminders_task,
    notify_newsletter_subscription_task,
)

pytestmark = [pytest.mark.anyio, pytest.mark.unit]


class TestWorkerTaskImports:
    """Test that worker tasks are properly defined and importable."""

    def test_send_signup_confirmation_task_exists(self) -> None:
        """Test send_signup_confirmation_task is callable."""
        assert callable(send_signup_confirmation_task)

    def test_send_waitlist_promoted_task_exists(self) -> None:
        """Test send_waitlist_promoted_task is callable."""
        assert callable(send_waitlist_promoted_task)

    def test_send_signup_cancelled_task_exists(self) -> None:
        """Test send_signup_cancelled_task is callable."""
        assert callable(send_signup_cancelled_task)

    def test_send_caregiver_message_task_exists(self) -> None:
        """Test send_caregiver_message_task is callable."""
        assert callable(send_caregiver_message_task)

    def test_send_session_cancelled_task_exists(self) -> None:
        """Test send_session_cancelled_task is callable."""
        assert callable(send_session_cancelled_task)

    def test_send_occurrence_cancelled_task_exists(self) -> None:
        """Test send_occurrence_cancelled_task is callable."""
        assert callable(send_occurrence_cancelled_task)

    def test_process_signup_approval_task_exists(self) -> None:
        """Test process_signup_approval_task is callable."""
        assert callable(process_signup_approval_task)

    def test_bulk_promote_waitlist_task_exists(self) -> None:
        """Test bulk_promote_waitlist_task is callable."""
        assert callable(bulk_promote_waitlist_task)

    def test_bulk_withdraw_signups_task_exists(self) -> None:
        """Test bulk_withdraw_signups_task is callable."""
        assert callable(bulk_withdraw_signups_task)

    def test_send_session_reminder_task_exists(self) -> None:
        """Test send_session_reminder_task is callable."""
        assert callable(send_session_reminder_task)

    def test_process_session_reminders_task_exists(self) -> None:
        """Test process_session_reminders_task is callable."""
        assert callable(process_session_reminders_task)

    def test_notify_newsletter_subscription_task_exists(self) -> None:
        """Test notify_newsletter_subscription_task is callable."""
        assert callable(notify_newsletter_subscription_task)
