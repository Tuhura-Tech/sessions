"""Integration tests for worker tasks with real database data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import models as m
from app.lib.worker import (
    bulk_promote_waitlist_task,
    bulk_withdraw_signups_task,
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
from tests.integration.test_fixtures import (
    create_test_block,
    create_test_caregiver,
    create_test_location,
    create_test_session,
    create_test_student,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


tz = ZoneInfo("Pacific/Auckland")


class DummyQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def enqueue(self, task_name: str, **kwargs: Any) -> None:
        self.calls.append((task_name, kwargs))


def _patch_worker_db(
    monkeypatch: pytest.MonkeyPatch,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async def _get_db_session_override() -> AsyncSession:
        return sessionmaker()

    monkeypatch.setattr("app.lib.worker._get_db_session", _get_db_session_override)


@pytest.mark.anyio
async def test_process_signup_approval_confirms_when_eligible_and_space(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    caregiver = await create_test_caregiver(db_session)
    student = await create_test_student(db_session, caregiver=caregiver)
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location, capacity=2)

    signup = m.Signup(
        student_id=student.id,
        session_id=session.id,
        status="pending",
    )
    db_session.add(signup)
    await db_session.commit()

    queue = DummyQueue()
    result = await process_signup_approval_task(
        {"queue": queue},
        signup_id=str(signup.id),
        caregiver_id=str(caregiver.id),
        student_id=str(student.id),
        session_id=str(session.id),
    )

    assert result["success"] is True
    assert result["final_status"] == "confirmed"

    await db_session.refresh(signup)
    assert signup.status == "confirmed"
    assert queue.calls
    assert queue.calls[0][0] == "send_signup_confirmation_task"


@pytest.mark.anyio
async def test_process_signup_approval_waitlists_when_full(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    caregiver = await create_test_caregiver(db_session)
    student = await create_test_student(db_session, caregiver=caregiver)
    other_caregiver = await create_test_caregiver(
        db_session, email="other@example.com", name="Other"
    )
    other_student = await create_test_student(
        db_session, caregiver=other_caregiver, name="Other Student"
    )
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location, capacity=1)

    confirmed = m.Signup(
        student_id=other_student.id,
        session_id=session.id,
        status="confirmed",
    )
    pending = m.Signup(
        student_id=student.id,
        session_id=session.id,
        status="pending",
    )
    db_session.add_all([confirmed, pending])
    await db_session.commit()

    queue = DummyQueue()
    result = await process_signup_approval_task(
        {"queue": queue},
        signup_id=str(pending.id),
        caregiver_id=str(caregiver.id),
        student_id=str(student.id),
        session_id=str(session.id),
    )

    assert result["success"] is True
    assert result["final_status"] == "waitlisted"

    await db_session.refresh(pending)
    assert pending.status == "waitlisted"
    assert queue.calls
    assert queue.calls[0][0] == "send_signup_confirmation_task"
    assert queue.calls[0][1]["signup_status"] == "waitlisted"


@pytest.mark.anyio
async def test_bulk_promote_waitlist_promotes_oldest_first(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    caregiver = await create_test_caregiver(db_session)
    student_old = await create_test_student(db_session, caregiver=caregiver)
    student_new = await create_test_student(
        db_session, caregiver=caregiver, name="New Student"
    )
    student_third = await create_test_student(
        db_session, caregiver=caregiver, name="Third Student"
    )
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location, capacity=2)

    confirmed = m.Signup(
        student_id=student_old.id,
        session_id=session.id,
        status="confirmed",
    )
    waitlisted_old = m.Signup(
        student_id=student_new.id,
        session_id=session.id,
        status="waitlisted",
    )
    waitlisted_old.created_at = datetime.now(timezone.utc) - timedelta(days=2)
    waitlisted_new = m.Signup(
        student_id=student_third.id,
        session_id=session.id,
        status="waitlisted",
    )
    waitlisted_new.created_at = datetime.now(timezone.utc) - timedelta(days=1)

    db_session.add_all([confirmed, waitlisted_old, waitlisted_new])
    await db_session.commit()

    queue = DummyQueue()
    result = await bulk_promote_waitlist_task(
        {"queue": queue},
        session_id=str(session.id),
        count=5,
    )

    assert result["success"] is True
    assert result["promoted"] == 1

    await db_session.refresh(waitlisted_old)
    await db_session.refresh(waitlisted_new)
    assert waitlisted_old.status == "confirmed"
    assert waitlisted_new.status == "waitlisted"

    assert len(queue.calls) == 1
    assert queue.calls[0][0] == "send_waitlist_promoted_task"


@pytest.mark.anyio
async def test_bulk_withdraw_signups_withdraws_and_enqueues(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    caregiver = await create_test_caregiver(db_session)
    student_one = await create_test_student(db_session, caregiver=caregiver)
    student_two = await create_test_student(
        db_session, caregiver=caregiver, name="Second Student"
    )
    student_three = await create_test_student(
        db_session, caregiver=caregiver, name="Third Student"
    )
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)

    confirmed = m.Signup(
        student_id=student_one.id,
        session_id=session.id,
        status="confirmed",
    )
    waitlisted = m.Signup(
        student_id=student_two.id,
        session_id=session.id,
        status="waitlisted",
    )
    withdrawn = m.Signup(
        student_id=student_three.id,
        session_id=session.id,
        status="withdrawn",
    )

    db_session.add_all([confirmed, waitlisted, withdrawn])
    await db_session.commit()

    queue = DummyQueue()
    result = await bulk_withdraw_signups_task(
        {"queue": queue},
        session_id=str(session.id),
        reason="Cancelled",
    )

    assert result["success"] is True
    assert result["withdrawn"] == 2

    await db_session.refresh(confirmed)
    await db_session.refresh(waitlisted)
    await db_session.refresh(withdrawn)

    assert confirmed.status == "withdrawn"
    assert confirmed.withdrawn_at is not None
    assert waitlisted.status == "withdrawn"
    assert waitlisted.withdrawn_at is not None
    assert withdrawn.status == "withdrawn"
    assert withdrawn.withdrawn_at is None

    assert len(queue.calls) == 2
    assert queue.calls[0][0] == "send_signup_cancelled_task"


@pytest.mark.anyio
async def test_send_session_cancelled_task_sends_only_confirmed(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    caregiver = await create_test_caregiver(db_session)
    student_one = await create_test_student(db_session, caregiver=caregiver)
    student_two = await create_test_student(
        db_session, caregiver=caregiver, name="Second Student"
    )
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)

    confirmed = m.Signup(
        student_id=student_one.id,
        session_id=session.id,
        status="confirmed",
    )
    waitlisted = m.Signup(
        student_id=student_two.id,
        session_id=session.id,
        status="waitlisted",
    )

    db_session.add_all([confirmed, waitlisted])
    await db_session.commit()

    result = await send_session_cancelled_task(
        {},
        session_id=str(session.id),
        session_name=session.name,
        cancellation_date=datetime.now(tz).date().isoformat(),
    )

    assert result["success"] is True
    assert result["emails_sent"] == 1
    assert mock_send.await_count == 1


@pytest.mark.anyio
async def test_send_occurrence_cancelled_task_sends_only_confirmed(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    caregiver = await create_test_caregiver(db_session)
    student = await create_test_student(db_session, caregiver=caregiver)
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)
    block = await create_test_block(db_session)

    occurrence = m.Occurrence(
        session_id=session.id,
        block_id=block.id,
        starts_at=datetime.now(tz) + timedelta(days=5),
        ends_at=datetime.now(tz) + timedelta(days=5, hours=2),
        cancelled=False,
    )
    db_session.add(occurrence)

    confirmed = m.Signup(
        student_id=student.id,
        session_id=session.id,
        status="confirmed",
    )
    db_session.add(confirmed)
    await db_session.commit()

    result = await send_occurrence_cancelled_task(
        {},
        occurrence_id=str(occurrence.id),
        session_id=str(session.id),
        session_name=session.name,
        occurrence_date=occurrence.starts_at.date().isoformat(),
    )

    assert result["success"] is True
    assert result["emails_sent"] == 1
    assert mock_send.await_count == 1


@pytest.mark.anyio
async def test_process_session_reminders_queues_first_occurrence_only(
    db_session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_worker_db(monkeypatch, sessionmaker)

    queue = DummyQueue()

    async def _get_task_queue_override() -> DummyQueue:
        return queue

    monkeypatch.setattr("app.lib.deps.get_task_queue", _get_task_queue_override)

    caregiver = await create_test_caregiver(db_session)
    student = await create_test_student(db_session, caregiver=caregiver)
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)
    block = await create_test_block(db_session)

    now = datetime.now(tz)
    first_occurrence = m.Occurrence(
        session_id=session.id,
        block_id=block.id,
        starts_at=now + timedelta(days=7),
        ends_at=now + timedelta(days=7, hours=2),
        cancelled=False,
    )
    second_occurrence = m.Occurrence(
        session_id=session.id,
        block_id=block.id,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        cancelled=False,
    )
    db_session.add_all([first_occurrence, second_occurrence])

    signup = m.Signup(
        student_id=student.id,
        session_id=session.id,
        status="confirmed",
    )
    db_session.add(signup)
    await db_session.commit()

    result = await process_session_reminders_task({})

    assert result["success"] is True
    assert result["reminders_queued"] == 1
    assert len(queue.calls) == 1
    assert queue.calls[0][0] == "send_session_reminder_task"
    assert queue.calls[0][1]["days_until"] == 1


# ============================================================================
# Email-Sending Worker Task Tests (with real template rendering)
# ============================================================================


@pytest.mark.anyio
async def test_send_signup_confirmation_task_confirmed_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_signup_confirmation_task renders confirmed template successfully."""
    # Mock only the actual email sending, not template rendering
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_signup_confirmation_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        session_venue="Tech Hub",
        session_address="123 Tech St, Auckland",
        signup_status="confirmed",
        signup_id="test-signup-id",
        session_id="test-session-id",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    # Verify the email was composed correctly
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "✓ Confirmed" in call_args["subject"]
    assert "Johnny Doe" in call_args["subject"]
    assert "<html" in call_args["html"].lower()
    assert "confirmed" in call_args["text"].lower()


@pytest.mark.anyio
async def test_send_signup_confirmation_task_waitlisted_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_signup_confirmation_task renders waitlisted template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_signup_confirmation_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        session_venue="Tech Hub",
        session_address="123 Tech St, Auckland",
        signup_status="waitlisted",
        signup_id="test-signup-id",
        session_id="test-session-id",
        waitlist_reason="Session is currently full",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    # Verify the email was composed correctly
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "📋 Waitlisted" in call_args["subject"]
    assert "<html" in call_args["html"].lower()
    assert "waitlist" in call_args["text"].lower()


@pytest.mark.anyio
async def test_send_signup_confirmation_task_pending_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_signup_confirmation_task renders pending template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_signup_confirmation_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        session_venue="Tech Hub",
        session_address="123 Tech St, Auckland",
        signup_status="pending",
        signup_id="test-signup-id",
        session_id="test-session-id",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    # Verify the email was composed correctly
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "📌 Pending" in call_args["subject"]
    assert "<html" in call_args["html"].lower()
    assert "pending" in call_args["text"].lower()


@pytest.mark.anyio
async def test_send_waitlist_promoted_task_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_waitlist_promoted_task renders template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_waitlist_promoted_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        session_venue="Tech Hub",
        session_address="123 Tech St, Auckland",
        signup_id="test-signup-id",
        session_id="test-session-id",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    # Verify the email was composed correctly
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "confirmed" in call_args["subject"].lower()
    assert "<html" in call_args["html"].lower()


@pytest.mark.anyio
async def test_send_signup_cancelled_task_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_signup_cancelled_task renders template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_signup_cancelled_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        signup_id="test-signup-id",
        cancellation_reason="Unable to attend",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "cancelled" in call_args["subject"].lower()
    assert "<html" in call_args["html"].lower()


@pytest.mark.anyio
async def test_send_caregiver_message_task_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_caregiver_message_task renders template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    result = await send_caregiver_message_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        subject="Important Update",
        message="Please check your dashboard for updates.",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "important update" in call_args["subject"].lower()
    assert "<html" in call_args["html"].lower()


@pytest.mark.anyio
async def test_send_session_reminder_task_renders_template(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test send_session_reminder_task renders template successfully."""
    mock_send = AsyncMock(return_value=True)
    monkeypatch.setattr("app.lib.email.email_service.send", mock_send)

    tomorrow = datetime.now(tz) + timedelta(days=1)

    result = await send_session_reminder_task(
        {},
        to_email="caregiver@example.com",
        caregiver_name="Jane Doe",
        student_name="Johnny Doe",
        session_name="Python Coding Class",
        occurrence_date=tomorrow.date().isoformat(),
        days_until=1,
        signup_id="test-signup-id",
    )

    assert result["success"] is True
    assert result["to_email"] == "caregiver@example.com"
    assert mock_send.await_count == 1

    # Verify the email was composed correctly
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["caregiver@example.com"]
    assert "reminder" in call_args["subject"].lower()
    assert "<html" in call_args["html"].lower()
