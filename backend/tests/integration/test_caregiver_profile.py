"""
Integration tests for caregiver profile endpoints.
"""

from __future__ import annotations

import pytest
from litestar.status_codes import HTTP_200_OK
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.lib.auth import new_token, hash_token, session_expires_at


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


async def create_caregiver_session(db_session: AsyncSession) -> tuple[m.Caregiver, str]:
    caregiver = m.Caregiver(
        email="testcaregiver@test.com",
        email_verified=True,
        name="Test Caregiver",
        phone="+64 21 123 4567",
    )
    db_session.add(caregiver)
    await db_session.flush()

    token = new_token()
    token_hash = hash_token(token)
    session = m.CaregiverSession(
        caregiver_id=caregiver.id,
        token_hash=token_hash,
        expires_at=session_expires_at(),
    )
    db_session.add(session)
    await db_session.commit()
    return caregiver, token


class TestCaregiverProfileEndpoints:
    async def test_get_me_requires_auth(self, test_client):
        response = await test_client.get("/api/v1/me")
        assert response.status_code == 401

    async def test_get_me_with_auth(self, client, db_session: AsyncSession):
        caregiver, token = await create_caregiver_session(db_session)

        response = await client.get(
            "/api/v1/me",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["email"] == caregiver.email
        assert data["name"] == caregiver.name

    async def test_update_me_with_auth(self, client, db_session: AsyncSession):
        _, token = await create_caregiver_session(db_session)

        response = await client.patch(
            "/api/v1/me",
            json={"name": "Updated Caregiver", "phone": "+64 22 000 0000"},
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Caregiver"

    async def test_update_me_subscribe_newsletter(
        self, client, db_session: AsyncSession, monkeypatch
    ):
        _, token = await create_caregiver_session(db_session)

        class DummyQueue:
            async def enqueue(self, *args, **kwargs):
                return None

        async def fake_get_task_queue():
            return DummyQueue()

        monkeypatch.setattr(
            "app.domains.caregiver.controllers.caregiver.get_task_queue",
            fake_get_task_queue,
        )

        response = await client.patch(
            "/api/v1/me",
            json={
                "name": "Updated Caregiver",
                "phone": "+64 22 000 0000",
                "subscribeNewsletter": True,
            },
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
