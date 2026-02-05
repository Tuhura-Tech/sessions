"""
End-to-end flow test covering admin setup and caregiver signup.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_302_FOUND
from sqlalchemy import select

from app.db.models import Caregiver
from app.domains.admin.guards import ADMIN_SESSION_COOKIE, create_admin_session
from tests.integration.test_fixtures import create_session_cookie

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestEndToEndFlow:
    """Simulate full admin -> caregiver flow."""

    async def test_admin_to_caregiver_signup_flow(
        self, test_client, db_session, monkeypatch
    ):
        admin_token = create_admin_session(
            email="admin@example.com",
            provider="google",
            provider_user_id="admin-123",
        )
        test_client.cookies.set(ADMIN_SESSION_COOKIE, admin_token)

        # Admin creates block
        block_response = await test_client.post(
            "/api/v1/admin/blocks/",
            json={
                "year": 2026,
                "name": "Term 1",
                "blockType": "term",
                "start_date": "2026-02-01",
                "end_date": "2026-04-01",
            },
        )
        assert block_response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        block_id = block_response.json()["id"]

        # Admin creates location
        location_response = await test_client.post(
            "/api/v1/admin/locations/",
            json={
                "name": "Central Hub",
                "address": "123 Main St",
                "region": "Auckland",
                "lat": -36.8485,
                "lng": 174.7633,
                "contactName": "Alex Admin",
                "contactEmail": "admin@example.com",
            },
        )
        assert location_response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        location_id = location_response.json()["id"]

        # Admin creates exclusion date
        exclusion_response = await test_client.post(
            "/api/v1/admin/exclusions/",
            json={
                "year": 2026,
                "date": "2026-03-10",
                "reason": "Public holiday",
            },
        )
        assert exclusion_response.status_code in (HTTP_200_OK, HTTP_201_CREATED)

        # Admin creates session
        session_response = await test_client.post(
            "/api/v1/admin/sessions/",
            json={
                "year": 2026,
                "session_type": "term",
                "name": "After School Coding",
                "age_lower": 8,
                "age_upper": 12,
                "start_time": "15:00:00",
                "end_time": "17:00:00",
                "day_of_week": 1,
                "capacity": 10,
                "location_id": location_id,
                "blocks": [block_id],
                "archived": False,
            },
        )
        if session_response.status_code not in (HTTP_200_OK, HTTP_201_CREATED):
            print(f"Session creation failed: {session_response.status_code}")
            print(f"Response content: {session_response.content}")
        assert session_response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        session_id = session_response.json()["id"]

        # Caregiver requests magic link
        caregiver_email = f"caregiver-{uuid4().hex}@example.com"
        magic_link_response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": caregiver_email, "returnTo": "/account"},
        )
        assert magic_link_response.status_code == HTTP_200_OK
        debug_token = magic_link_response.json().get(
            "debugToken"
        ) or magic_link_response.json().get("debug_token")
        assert debug_token

        # Caregiver consumes magic link (exercise endpoint)
        consume_response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": debug_token, "returnTo": "/account"},
            follow_redirects=False,
        )
        assert consume_response.status_code == HTTP_302_FOUND

        # Create a caregiver session cookie we can reliably use in tests
        result = await db_session.execute(
            select(Caregiver).where(Caregiver.email == caregiver_email)
        )
        caregiver = result.scalar_one()
        caregiver_token, _ = await create_session_cookie(db_session, caregiver)
        test_client.cookies.set("caregiver_session", caregiver_token)
        caregiver_headers = {"Authorization": f"Bearer {caregiver_token}"}

        # Caregiver completes profile
        profile_response = await test_client.patch(
            "/api/v1/me",
            headers=caregiver_headers,
            json={"name": "Care Giver", "phone": "021000000"},
        )
        assert profile_response.status_code == HTTP_200_OK

        # Caregiver creates student
        student_response = await test_client.post(
            "/api/v1/students",
            headers=caregiver_headers,
            json={
                "name": "Student One",
                "date_of_birth": date(2016, 1, 1).isoformat(),
                "media_consent": True,
            },
        )
        assert student_response.status_code == HTTP_201_CREATED
        student_id = student_response.json()["id"]

        # Caregiver signs up student to session
        signup_response = await test_client.post(
            f"/api/v1/signups/{session_id}",
            headers=caregiver_headers,
            json={"studentId": student_id},
        )
        assert signup_response.status_code == HTTP_201_CREATED
        assert signup_response.json()["status"] in {
            "pending",
            "confirmed",
            "waitlisted",
        }

        # Caregiver can list signups
        list_signups_response = await test_client.get(
            "/api/v1/signups",
            headers=caregiver_headers,
        )
        assert list_signups_response.status_code == HTTP_200_OK
        assert len(list_signups_response.json()) > 0
