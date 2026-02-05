"""
Integration tests for caregiver student endpoints.

Tests for student CRUD operations with authentication.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.lib.auth import new_token, hash_token, session_expires_at

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestCaregiverStudentListEndpoint:
    """Test caregiver student listing endpoint."""

    async def test_list_students_requires_auth(self, test_client):
        """Test listing students without authentication returns 401."""
        response = await test_client.get("/api/v1/students/")
        assert response.status_code == 401

    async def test_list_students_with_data(self, client, db_session: AsyncSession):
        """Test listing students returns caregiver's students."""
        # Create caregiver with session
        caregiver = m.Caregiver(email="testcaregiver@test.com", email_verified=True)
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

        # Create students
        student1 = m.Student(
            caregiver_id=caregiver.id,
            name="Student One",
            date_of_birth=date.today() - timedelta(days=365 * 8),
        )
        student2 = m.Student(
            caregiver_id=caregiver.id,
            name="Student Two",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        db_session.add(student1)
        db_session.add(student2)
        await db_session.commit()

        response = await client.get(
            "/api/v1/students/",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestCaregiverStudentDetailEndpoint:
    """Test caregiver student detail endpoint."""

    async def test_get_student_requires_auth(self, test_client):
        """Test getting student without authentication returns 401."""
        fake_id = uuid4()
        response = await test_client.get(f"/api/v1/students/{fake_id}")
        assert response.status_code == 401

    async def test_get_student_with_auth(self, client, db_session: AsyncSession):
        """Test getting own student details."""
        caregiver = m.Caregiver(email="testcaregiver@test.com", email_verified=True)
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

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Test Student",
            date_of_birth=date.today() - timedelta(days=365 * 8),
        )
        db_session.add(student)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/students/{student.id}",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == str(student.id)
        assert data["name"] == "Test Student"


class TestCaregiverStudentCreateEndpoint:
    """Test caregiver student creation endpoint."""

    async def test_create_student_requires_auth(self, test_client):
        """Test creating student without authentication returns 401."""
        response = await test_client.post(
            "/api/v1/students/",
            json={
                "name": "Test Student",
                "dateOfBirth": "2015-01-15",
            },
        )
        assert response.status_code == 401

    async def test_create_student_with_valid_data(
        self, client, db_session: AsyncSession
    ):
        """Test creating a student with valid data."""
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

        response = await client.post(
            "/api/v1/students/",
            json={
                "name": "New Student",
                "dateOfBirth": "2015-01-15",
            },
            cookies={"caregiver_session": token},
        )
        assert response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        data = response.json()
        assert data["name"] == "New Student"


class TestCaregiverStudentUpdateEndpoint:
    """Test caregiver student update endpoint."""

    async def test_update_student_requires_auth(self, test_client):
        """Test updating student without authentication returns 401."""
        fake_id = uuid4()
        response = await test_client.patch(
            f"/api/v1/students/{fake_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 401

    async def test_update_student_with_auth(self, client, db_session: AsyncSession):
        """Test updating own student."""
        caregiver = m.Caregiver(email="testcaregiver@test.com", email_verified=True)
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

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Original Name",
            date_of_birth=date.today() - timedelta(days=365 * 8),
        )
        db_session.add(student)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/students/{student.id}",
            json={"name": "Updated Name"},
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"


class TestCaregiverStudentDeleteEndpoint:
    """Test caregiver student deletion endpoint."""

    async def test_delete_student_requires_auth(self, test_client):
        """Test deleting student without authentication returns 401."""
        fake_id = uuid4()
        response = await test_client.delete(f"/api/v1/students/{fake_id}")
        assert response.status_code == 401

    async def test_delete_student_with_auth(self, client, db_session: AsyncSession):
        """Test deleting own student."""
        caregiver = m.Caregiver(email="testcaregiver@test.com", email_verified=True)
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

        student = m.Student(
            caregiver_id=caregiver.id,
            name="Student to Delete",
            date_of_birth=date.today() - timedelta(days=365 * 8),
        )
        db_session.add(student)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/students/{student.id}",
            cookies={"caregiver_session": token},
        )
        assert response.status_code == HTTP_200_OK
