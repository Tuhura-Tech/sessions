"""Integration tests for admin queue notification behaviors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from tests.integration.test_fixtures import (
    create_test_block,
    create_test_caregiver,
    create_test_location,
    create_test_session,
    create_test_student,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class DummyQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def enqueue(self, task_name: str, **kwargs: Any) -> None:
        self.calls.append((task_name, kwargs))


@pytest.mark.anyio
async def test_admin_signup_status_enqueues_waitlist_promotion(
    client: AsyncClient,
    admin_session_cookie: str,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = DummyQueue()

    async def _get_task_queue() -> DummyQueue:
        return queue

    monkeypatch.setattr(
        "app.domains.admin.controllers.signups.get_task_queue",
        _get_task_queue,
    )

    caregiver = await create_test_caregiver(db_session)
    student = await create_test_student(db_session, caregiver=caregiver)
    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)

    signup = m.Signup(
        student_id=student.id,
        session_id=session.id,
        status="waitlisted",
    )
    db_session.add(signup)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/admin/signups/{signup.id}/status",
        cookies={"admin_session": admin_session_cookie},
        json={
            "status": "confirmed",
            "notify_caregiver": True,
        },
    )

    assert response.status_code == HTTP_200_OK
    assert queue.calls
    assert queue.calls[0][0] == "send_waitlist_promoted_task"


@pytest.mark.anyio
async def test_admin_occurrence_cancel_enqueues_notification(
    client: AsyncClient,
    admin_session_cookie: str,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = DummyQueue()

    async def _get_task_queue() -> DummyQueue:
        return queue

    monkeypatch.setattr(
        "app.domains.admin.controllers.occurrences.get_task_queue",
        _get_task_queue,
    )

    location = await create_test_location(db_session)
    session = await create_test_session(db_session, location=location)
    block = await create_test_block(db_session)

    starts_at = datetime.now(timezone.utc)
    occurrence = m.Occurrence(
        session_id=session.id,
        block_id=block.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        cancelled=False,
    )
    db_session.add(occurrence)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/admin/occurrences/{occurrence.id}/cancel?cancelled=true",
        cookies={"admin_session": admin_session_cookie},
    )

    assert response.status_code == HTTP_200_OK
    assert queue.calls
    assert queue.calls[0][0] == "send_occurrence_cancelled_task"


@pytest.mark.anyio
async def test_admin_caregiver_create_subscribe_enqueues_newsletter(
    client: AsyncClient,
    admin_session_cookie: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = DummyQueue()

    async def _get_task_queue() -> DummyQueue:
        return queue

    monkeypatch.setattr(
        "app.domains.admin.controllers.caregiver.get_task_queue",
        _get_task_queue,
    )

    response = await client.post(
        "/api/v1/admin/caregivers/",
        cookies={"admin_session": admin_session_cookie},
        json={
            "email": "news@example.com",
            "name": "Newsletter User",
            "emailVerified": True,
            "subscribeNewsletter": True,
        },
    )

    assert response.status_code == HTTP_201_CREATED
    assert queue.calls
    assert queue.calls[0][0] == "notify_newsletter_subscription_task"


@pytest.mark.anyio
async def test_admin_email_caregiver_enqueues_message_task(
    client: AsyncClient,
    admin_session_cookie: str,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = DummyQueue()

    async def _get_task_queue() -> DummyQueue:
        return queue

    monkeypatch.setattr(
        "app.domains.admin.controllers.caregiver.get_task_queue",
        _get_task_queue,
    )

    caregiver = await create_test_caregiver(db_session, email="msg@example.com")

    response = await client.post(
        f"/api/v1/admin/caregivers/{caregiver.id}/email",
        cookies={"admin_session": admin_session_cookie},
        json={
            "subject": "Hello",
            "message": "A quick note",
        },
    )

    # Email endpoint returns 200 for Litestar <2.10, 201 for newer versions
    assert response.status_code in [HTTP_200_OK, HTTP_201_CREATED]
    assert queue.calls
    assert queue.calls[0][0] == "send_caregiver_message_task"
