"""
Integration tests for caregiver signup endpoints.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.lib.auth import new_token, hash_token, session_expires_at, utcnow
from tests.integration.test_fixtures import create_test_location, create_test_session


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


class TestCaregiverSignupListEndpoint:
    async def test_list_signups_requires_auth(self, test_client):
        response = await test_client.get("/api/v1/signups/")
        assert response.status_code == 401

    async def test_list_signups_with_data(self, client, db_session: AsyncSession):
        caregiver, token = await create_caregiver_session(db_session)
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student One",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.get(
            "/api/v1/signups/",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        session_id = data[0].get("sessionId") or data[0].get("session_id")
        student_id = data[0].get("studentId") or data[0].get("student_id")
        assert session_id == str(session.id)
        assert student_id == str(student.id)


class TestCaregiverSignupCreateEndpoint:
    async def test_create_signup_requires_auth(self, test_client):
        response = await test_client.post(
            f"/api/v1/signups/{uuid4()}",
            json={"studentId": str(uuid4())},
        )
        assert response.status_code == 401

    async def test_create_signup_invalid_student_id(self, client, db_session):
        _, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)

        response = await client.post(
            f"/api/v1/signups/{session.id}",
            json={"studentId": "not-a-uuid"},
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_create_signup_existing_non_withdrawn(self, client, db_session):
        caregiver, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student Existing",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/signups/{session.id}",
            json={"studentId": str(student.id)},
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_create_signup_reactivate_withdrawn(self, client, db_session):
        caregiver, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student Withdrawn",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="withdrawn",
            withdrawn_at=utcnow(),
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/signups/{session.id}",
            json={"studentId": str(student.id), "needsDevices": True},
            cookies={"caregiver_session": token},
        )
        assert response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        data = response.json()
        assert data["status"] == "pending"

    async def test_create_signup_new(self, client, db_session):
        caregiver, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student New",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/signups/{session.id}",
            json={"studentId": str(student.id), "pickupDropoff": "parent"},
            cookies={"caregiver_session": token},
        )
        assert response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        data = response.json()
        assert data["status"] == "pending"


class TestCaregiverSignupWithdrawEndpoint:
    async def test_withdraw_signup_requires_auth(self, test_client):
        response = await test_client.delete(f"/api/v1/signups/{uuid4()}")
        assert response.status_code == 401

    async def test_withdraw_signup_already_withdrawn(self, client, db_session):
        caregiver, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student Withdrawn",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="withdrawn",
            withdrawn_at=utcnow(),
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/signups/{signup.id}",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        assert response.json()["message"] == "Signup already withdrawn"

    async def test_withdraw_signup_success(self, client, db_session):
        caregiver, token = await create_caregiver_session(db_session)
        session = await create_test_session(db_session)
        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student Active",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student)
        await db_session.flush()

        signup = m.Signup(
            session_id=session.id,
            student_id=student.id,
            status="confirmed",
        )
        db_session.add(signup)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/signups/{signup.id}",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        assert response.json()["message"] == "Signup withdrawn successfully"
