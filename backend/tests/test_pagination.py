"""
Tests for pagination functionality in admin controllers.
"""

import pytest
from datetime import date, time
from httpx import AsyncClient

from app.db import models as m

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


async def test_sessions_list_with_pagination(client: AsyncClient, admin_session_cookie: str, db_session):
    """Test that sessions list endpoint supports pagination parameters."""
    # Create multiple sessions
    location = m.Location(
        name="Test Location",
        address="123 Test St",
        region="Test Region",
        lat=-36.8485,
        lng=174.7633,
        contact_name="Test Contact",
        contact_email="contact@test.com",
    )
    db_session.add(location)
    await db_session.flush()

    sessions = [
        m.Session(
            location_id=location.id,
            year=2026,
            session_type="term",
            name=f"Session {i}",
            age_lower=8,
            age_upper=12,
            day_of_week=1,
            start_time=time(14, 0),
            end_time=time(16, 0),
            capacity=20,
        )
        for i in range(15)
    ]
    db_session.add_all(sessions)
    await db_session.commit()

    # Test default pagination
    response = await client.get(
        "/api/v1/admin/sessions",
        cookies={"admin_session": admin_session_cookie},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 15

    # Test with limit
    response = await client.get(
        "/api/v1/admin/sessions?limit=5",
        cookies={"admin_session": admin_session_cookie},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] == 15


async def test_students_list_with_pagination(client: AsyncClient, admin_session_cookie: str, db_session):
    """Test that students list endpoint supports pagination parameters."""
    # Create caregiver
    caregiver = m.Caregiver(
        email="test@example.com",
        name="Test Caregiver",
        phone="021 123 4567",
    )
    db_session.add(caregiver)
    await db_session.flush()

    # Create multiple students
    students = [
        m.Student(
            caregiver_id=caregiver.id,
            name=f"Student{i} Test",
            date_of_birth=date(2015, 1, 1),
        )
        for i in range(20)
    ]
    db_session.add_all(students)
    await db_session.commit()

    # Test with pagination
    response = await client.get(
        "/api/v1/admin/students?limit=10&offset=5",
        cookies={"admin_session": admin_session_cookie},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 20
