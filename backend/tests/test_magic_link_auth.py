#!/usr/bin/env python3
"""
Comprehensive tests for the magic link authentication flow.

Tests cover:
- Request magic link with valid/invalid email
- Token generation and validation
- Token expiration
- Token reuse prevention
- Session creation after consumption
- Redirect handling
- Email normalization

Run with: pytest tests/test_magic_link_auth.py -v
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from app.db.models import CaregiverMagicLink, Caregiver

pytestmark = pytest.mark.anyio


class TestMagicLinkRequest:
    """Tests for requesting a magic link."""

    async def test_request_magic_link_with_valid_email(self, test_client, session):
        """Test requesting a magic link with a valid email address."""
        test_email = f"valid-{uuid4().hex}@example.com"

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "debugToken" in data or "debug_token" in data

        # Verify caregiver was created
        result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver = result.scalar_one_or_none()
        assert caregiver is not None
        assert caregiver.email == test_email.lower()

    async def test_request_magic_link_with_invalid_email(self, test_client):
        """Test that invalid email is rejected."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "not-an-email"},
        )

        assert response.status_code in [400, 422]

    async def test_request_magic_link_missing_email(self, test_client):
        """Test that missing email is rejected."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={},
        )

        assert response.status_code in [400, 422]

    async def test_request_magic_link_creates_magic_link_record(
        self, test_client, session
    ):
        """Test that a magic link record is created in the database."""
        test_email = f"link-{uuid4().hex}@example.com"

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )

        assert response.status_code == 200
        data = response.json()
        token = data.get("debugToken") or data.get("debug_token")
        assert token is not None

        # Find caregiver
        caregiver_result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver = caregiver_result.scalar_one_or_none()
        assert caregiver is not None

        # Verify magic link record exists
        links_result = await session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.caregiver_id == caregiver.id
            )
        )
        magic_link = links_result.scalar_one_or_none()
        assert magic_link is not None
        assert magic_link.used_at is None
        assert magic_link.expires_at > datetime.now(timezone.utc)

    async def test_request_magic_link_with_return_to(self, test_client):
        """Test that return_to parameter is accepted."""
        test_email = f"return-{uuid4().hex}@example.com"
        return_to = "/some/return/path"

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email, "return_to": return_to},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    async def test_request_magic_link_email_normalization(self, test_client, session):
        """Test that email is normalized (lowercased and stripped)."""
        original_email = f"  TEST-{uuid4().hex}@EXAMPLE.COM  "
        normalized_email = original_email.strip().lower()

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": original_email},
        )

        assert response.status_code == 200

        # Verify email was normalized in database
        result = await session.execute(
            select(Caregiver).where(Caregiver.email == normalized_email)
        )
        caregiver = result.scalar_one_or_none()
        assert caregiver is not None
        assert caregiver.email == normalized_email

    async def test_request_magic_link_debug_mode_response(self, test_client):
        """Test that debug token is returned in debug mode."""
        test_email = f"debug-{uuid4().hex}@example.com"

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )

        assert response.status_code == 200
        data = response.json()
        # In debug mode, debugToken should be present
        token = data.get("debugToken") or data.get("debug_token")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0


class TestMagicLinkConsumption:
    """Tests for consuming a magic link."""

    async def test_consume_valid_magic_link(self, test_client):
        """Test consuming a valid magic link."""
        test_email = f"consume-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        assert response.status_code == 200
        token = response.json().get("debugToken") or response.json().get("debug_token")
        assert token is not None

        # Consume magic link
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location is not None

    async def test_consume_invalid_token(self, test_client):
        """Test that invalid token is rejected."""
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": "invalid-token-12345"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert (
            "Invalid" in data.get("error", "")
            or "expired" in data.get("error", "").lower()
        )

    async def test_consume_token_marks_as_used(self, test_client, session):
        """Test that consuming a token marks it as used."""
        test_email = f"mark-used-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Find caregiver and get initial state
        caregiver_result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver = caregiver_result.scalar_one_or_none()

        # Get magic link before consumption
        link_before = await session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.caregiver_id == caregiver.id
            )
        )
        magic_link_before = link_before.scalar_one_or_none()
        assert magic_link_before.used_at is None

        # Consume token
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Refresh and check if marked as used
        await session.refresh(magic_link_before)
        assert magic_link_before.used_at is not None

    async def test_consume_token_prevents_reuse(self, test_client):
        """Test that a token cannot be used twice."""
        test_email = f"no-reuse-{uuid4().hex}@example.com"

        # Request and consume once
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # First consumption
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Second consumption attempt (should fail)
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False

    async def test_consume_sets_session_cookie(self, test_client):
        """Test that consuming a token sets the session cookie."""
        test_email = f"session-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Consume token
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify session cookie is set
        cookies = response.cookies
        set_cookie = response.headers.get("set-cookie")
        assert "caregiver_session" in cookies or (
            set_cookie and "caregiver_session" in set_cookie
        )

    async def test_consume_with_return_to(self, test_client):
        """Test that returnTo parameter is respected in redirect."""
        test_email = f"return-to-{uuid4().hex}@example.com"
        return_to = "/account/settings"

        # Request magic link with return_to
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email, "return_to": return_to},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Consume with returnTo
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token, "returnTo": return_to},
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("Location")
        assert return_to in location

    async def test_consume_verifies_caregiver_email(self, test_client, session):
        """Test that consuming a token marks email as verified."""
        test_email = f"verify-email-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Find caregiver before consumption
        caregiver_result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver_before = caregiver_result.scalar_one_or_none()
        assert caregiver_before.email_verified is False

        # Consume token
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Check email_verified is now True
        await session.refresh(caregiver_before)
        assert caregiver_before.email_verified is True

    async def test_consume_updates_last_login(self, test_client, session):
        """Test that consuming a token updates last_login_at."""
        test_email = f"last-login-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Find caregiver before consumption
        caregiver_result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver_before = caregiver_result.scalar_one_or_none()
        last_login_before = caregiver_before.last_login_at

        # Consume token
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Check last_login_at was updated
        await session.refresh(caregiver_before)
        assert caregiver_before.last_login_at is not None
        assert caregiver_before.last_login_at > (
            last_login_before or datetime.min.replace(tzinfo=timezone.utc)
        )


class TestMagicLinkEdgeCases:
    """Tests for edge cases and error conditions."""

    async def test_empty_token_rejected(self, test_client):
        """Test that empty token is rejected."""
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": ""},
        )

        assert response.status_code == 400

    async def test_missing_token_rejected(self, test_client):
        """Test that missing token is rejected."""
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={},
        )

        assert response.status_code in [400, 422]

    async def test_request_with_empty_email(self, test_client):
        """Test that empty email is rejected."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": ""},
        )

        assert response.status_code in [400, 422]

    async def test_consume_safe_redirect(self, test_client):
        """Test that consume endpoint prevents open redirect attacks."""
        test_email = f"redirect-{uuid4().hex}@example.com"

        # Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        token = response.json().get("debugToken") or response.json().get("debug_token")

        # Try to redirect to external URL
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={
                "token": token,
                "returnTo": "https://attacker.com/evil",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("Location")
        # Should not redirect to attacker.com
        assert "attacker.com" not in location


class TestMagicLinkCompleteFlow:
    """Integration tests for complete magic link flows."""

    async def test_complete_magic_link_flow(self, test_client, session):
        """Test complete flow: request → consume → verify authenticated."""
        test_email = f"complete-{uuid4().hex}@example.com"
        return_to = "/dashboard"

        # Step 1: Request magic link
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email, "return_to": return_to},
        )
        assert response.status_code == 200
        token = response.json().get("debugToken") or response.json().get("debug_token")
        assert token is not None

        # Step 2: Verify caregiver was created
        caregiver_result = await session.execute(
            select(Caregiver).where(Caregiver.email == test_email.lower())
        )
        caregiver = caregiver_result.scalar_one_or_none()
        assert caregiver is not None

        # Step 3: Consume magic link
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token, "returnTo": return_to},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert return_to in response.headers.get("Location", "")

        # Step 4: Verify session is set
        assert (
            response.headers.get("set-cookie")
            or "caregiver_session" in response.cookies
        )

        # Step 5: Verify caregiver state
        await session.refresh(caregiver)
        assert caregiver.email_verified is True
        assert caregiver.last_login_at is not None

    async def test_multiple_users_independent_tokens(self, test_client):
        """Test that different users have independent magic links."""
        user1_email = f"user1-{uuid4().hex}@example.com"
        user2_email = f"user2-{uuid4().hex}@example.com"

        # User 1 requests magic link
        response1 = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": user1_email},
        )
        token1 = response1.json().get("debugToken") or response1.json().get(
            "debug_token"
        )

        # User 2 requests magic link
        response2 = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": user2_email},
        )
        token2 = response2.json().get("debugToken") or response2.json().get(
            "debug_token"
        )

        # Tokens should be different
        assert token1 != token2

        # User 1 consumes their token
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token1},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # User 2's token should still work
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": token2},
            follow_redirects=False,
        )
        assert response.status_code == 302
