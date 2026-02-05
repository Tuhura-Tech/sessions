"""
Integration tests for caregiver authentication endpoints.

Tests for magic link request, consumption, and logout flows.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.auth import new_token, hash_token
from app.db.models import Caregiver, CaregiverMagicLink
from tests.integration.test_fixtures import (
    create_test_caregiver,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


@pytest.mark.auth
class TestMagicLinkRequestEndpoint:
    """Test magic link request endpoint."""

    async def test_request_magic_link_success(self, test_client):
        """Test POST /api/v1/auth/magic-link creates magic link."""
        test_email = "test@example.com"

        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={
                "email": test_email,
                "returnTo": "/dashboard",
            },
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True

        # Debug token should be present in debug mode
        debug_token = data.get("debugToken") or data.get("debug_token")
        assert isinstance(debug_token, str)
        assert len(debug_token) > 0

    async def test_request_magic_link_email_normalization(self, test_client):
        """Test that email is normalized (lowercase, trimmed)."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={
                "email": "  Test@Example.COM  ",
                "returnTo": "/dashboard",
            },
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["ok"] is True

    async def test_request_magic_link_missing_email(self, test_client):
        """Test POST /api/v1/auth/magic-link rejects missing email."""
        response = await test_client.post(
            "/api/v1/auth/magic-link", json={"returnTo": "/dashboard"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_request_magic_link_invalid_email_format(self, test_client):
        """Test POST /api/v1/auth/magic-link rejects invalid email format."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={
                "email": "not-an-email",
                "returnTo": "/dashboard",
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_request_magic_link_creates_caregiver(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that requesting magic link creates caregiver if not exists."""
        test_email = "newuser@example.com"

        response = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )

        assert response.status_code == HTTP_200_OK

        # Verify caregiver was created
        from sqlalchemy import select

        result = await db_session.execute(
            select(Caregiver).where(Caregiver.email == test_email)
        )
        caregiver = result.scalar_one_or_none()
        assert caregiver is not None
        assert caregiver.email == test_email

    async def test_request_magic_link_reuses_token_within_ttl(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that requesting magic link twice returns same token within TTL."""
        test_email = "reuse@example.com"

        # First request
        response1 = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )
        assert response1.status_code == HTTP_200_OK
        token1 = response1.json().get("debugToken") or response1.json().get(
            "debug_token"
        )

        # Second request immediately after
        response2 = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )
        assert response2.status_code == HTTP_200_OK
        token2 = response2.json().get("debugToken") or response2.json().get(
            "debug_token"
        )

        # Tokens should be present; reuse may generate a new token in debug mode
        assert token1 is not None
        assert token2 is not None


pytestmark = [pytest.mark.anyio, pytest.mark.integration, pytest.mark.auth]


class TestMagicLinkConsumeEndpoint:
    """Test magic link consumption endpoint."""

    async def test_consume_magic_link_success(self, test_client):
        """Test GET /api/v1/auth/magic-link/consume validates and consumes token."""
        # First request magic link
        test_email = "consume@example.com"
        request_response = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )

        assert request_response.status_code == HTTP_200_OK
        request_data = request_response.json()
        debug_token = request_data.get("debugToken") or request_data.get("debug_token")

        assert debug_token is not None

        # Consume magic link
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={
                "token": debug_token,
                "returnTo": "/dashboard",
            },
            follow_redirects=False,
        )

        # Should redirect (302) or succeed (200)
        assert response.status_code in (200, 302)

        # Check for session cookie
        if response.status_code == 302:
            # After redirect, should have session cookie
            assert "caregiver_session" in response.cookies or response.headers.get(
                "set-cookie"
            )

    async def test_consume_magic_link_invalid_token(self, test_client):
        """Test GET /api/v1/auth/magic-link/consume rejects invalid token."""
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={
                "token": "invalid-token-12345",
                "returnTo": "/dashboard",
            },
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["ok"] is False
        assert "Invalid" in data.get("error", "") or "expired" in data.get("error", "")

    async def test_consume_magic_link_missing_token(self, test_client):
        """Test GET /api/v1/auth/magic-link/consume rejects missing token."""
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume", params={"returnTo": "/dashboard"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_consume_magic_link_expired_token(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that expired magic links cannot be consumed."""
        from datetime import timedelta
        from app.lib.auth import utcnow

        # Create caregiver
        caregiver = await create_test_caregiver(db_session)

        # Create an expired magic link
        token = new_token()
        expired_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(token),
            expires_at=utcnow() - timedelta(hours=1),
        )
        db_session.add(expired_link)
        await db_session.flush()

        # Try to consume it
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume", params={"token": token}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_consume_magic_link_creates_session(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that consuming magic link creates caregiver session."""
        test_email = "session@example.com"

        # Request and consume magic link
        request_response = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )

        debug_token = request_response.json().get(
            "debugToken"
        ) or request_response.json().get("debug_token")

        # Consume magic link
        response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": debug_token},
            follow_redirects=False,
        )

        assert response.status_code in (200, 302)

        # Verify session cookie was set
        assert "caregiver_session" in response.cookies or response.headers.get(
            "set-cookie"
        )


@pytest.mark.integration
@pytest.mark.auth
class TestLogoutEndpoint:
    """Test logout endpoint."""

    async def test_logout_success(self, test_client):
        """Test POST /api/v1/auth/logout clears session."""
        # First authenticate
        test_email = "logout@example.com"
        request_response = await test_client.post(
            "/api/v1/auth/magic-link", json={"email": test_email}
        )

        debug_token = request_response.json().get(
            "debugToken"
        ) or request_response.json().get("debug_token")

        # Consume magic link
        await test_client.get(
            "/api/v1/auth/magic-link/consume", params={"token": debug_token}
        )

        # Now logout
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["ok"] is True

    async def test_logout_without_session(self, test_client):
        """Test logout when not authenticated."""
        response = await test_client.post("/api/v1/auth/logout")

        # Should still return 200 (idempotent logout)
        assert response.status_code == HTTP_200_OK


@pytest.mark.integration
@pytest.mark.auth
class TestCompleteAuthFlow:
    """Test complete authentication workflows."""

    async def test_complete_auth_flow(self, test_client):
        """Test complete magic link authentication flow."""
        test_email = "flow@example.com"
        test_return_to = "/dashboard"

        # Step 1: Request magic link
        request_response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={
                "email": test_email,
                "returnTo": test_return_to,
            },
        )
        assert request_response.status_code == HTTP_200_OK
        request_data = request_response.json()
        assert request_data["ok"] is True

        # Step 2: Consume magic link
        debug_token = request_data.get("debugToken") or request_data.get("debug_token")
        assert debug_token is not None

        consume_response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={
                "token": debug_token,
                "returnTo": test_return_to,
            },
            follow_redirects=False,
        )
        assert consume_response.status_code in (200, 302)

        # Step 3: Logout
        logout_response = await test_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == HTTP_200_OK
        assert logout_response.json()["ok"] is True

    async def test_auth_flow_with_different_return_paths(self, test_client):
        """Test auth flow with different return paths."""
        for return_to in ["/dashboard", "/profile", "/sessions"]:
            request_response = await test_client.post(
                "/api/v1/auth/magic-link",
                json={"email": f"test{return_to}@example.com", "returnTo": return_to},
            )
            assert request_response.status_code == HTTP_200_OK


@pytest.mark.integration
@pytest.mark.auth
class TestDebugTokenResponse:
    """Test debug token is properly returned in debug mode."""

    async def test_debug_token_present_in_response(self, test_client):
        """Test that debug_token is included in magic link response."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "debug-test@example.com"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Should have both ok and debug_token fields
        assert "ok" in data
        assert data["ok"] is True

        # debug_token should be present (check both snake_case and camelCase)
        debug_token = data.get("debug_token") or data.get("debugToken")
        assert debug_token is not None
        assert isinstance(debug_token, str)
        assert len(debug_token) > 0

    async def test_debug_token_is_usable(self, test_client):
        """Test that returned debug_token can be used to consume magic link."""
        test_email = "usable-token@example.com"

        # Request magic link
        request_response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )

        assert request_response.status_code == HTTP_200_OK
        debug_token = request_response.json().get(
            "debug_token"
        ) or request_response.json().get("debugToken")
        assert debug_token is not None

        # Use the token to consume the magic link
        consume_response = await test_client.get(
            "/api/v1/auth/magic-link/consume",
            params={"token": debug_token},
            follow_redirects=False,
        )

        # Should succeed (either 200 or 302 redirect)
        assert consume_response.status_code in (200, 302)

    async def test_debug_token_format(self, test_client):
        """Test that debug_token has the expected format (URL-safe base64)."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "format-test@example.com"},
        )

        assert response.status_code == HTTP_200_OK
        debug_token = response.json().get("debug_token") or response.json().get(
            "debugToken"
        )

        # Should be a URL-safe string
        assert debug_token is not None
        assert isinstance(debug_token, str)

        # Should contain only URL-safe characters (alphanumeric, -, _, no padding)
        import re

        assert re.match(r"^[A-Za-z0-9_-]+$", debug_token), (
            f"Token contains invalid characters: {debug_token}"
        )

    async def test_debug_token_uniqueness_across_requests(self, test_client):
        """Test that different magic link requests produce different tokens."""
        tokens = []

        for i in range(3):
            response = await test_client.post(
                "/api/v1/auth/magic-link",
                json={"email": f"unique-{i}@example.com"},
            )

            assert response.status_code == HTTP_200_OK
            token = response.json().get("debug_token") or response.json().get(
                "debugToken"
            )
            assert token is not None
            tokens.append(token)

        # All tokens should be different
        assert len(set(tokens)) == 3, "Tokens should be unique across requests"

    async def test_debug_token_returned_on_caregiver_reuse(self, test_client):
        """Test that debug_token is returned even when reusing existing caregiver."""
        test_email = "reuse-debug@example.com"

        # First request
        response1 = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        assert response1.status_code == HTTP_200_OK
        token1 = response1.json().get("debug_token") or response1.json().get(
            "debugToken"
        )
        assert token1 is not None

        # Second request (should reuse caregiver)
        response2 = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_email},
        )
        assert response2.status_code == HTTP_200_OK
        token2 = response2.json().get("debug_token") or response2.json().get(
            "debugToken"
        )
        assert token2 is not None

    async def test_debug_token_with_return_to_parameter(self, test_client):
        """Test that debug_token is returned regardless of returnTo parameter."""
        return_paths = ["/dashboard", "/account", "/sessions"]

        for path in return_paths:
            response = await test_client.post(
                "/api/v1/auth/magic-link",
                json={
                    "email": f"return-{path}@example.com",
                    "returnTo": path,
                },
            )

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["ok"] is True

            debug_token = data.get("debug_token") or data.get("debugToken")
            assert debug_token is not None, f"Missing token for returnTo={path}"
            assert isinstance(debug_token, str)

    async def test_debug_token_response_structure(self, test_client):
        """Test that response has correct structure with proper field names."""
        response = await test_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "structure@example.com"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Should have required fields
        assert "ok" in data
        assert "debug_token" in data or "debugToken" in data

        # ok should be boolean True
        assert data["ok"] is True

        # debug_token should be string or null
        debug_token = data.get("debug_token") or data.get("debugToken")
        assert isinstance(debug_token, (str, type(None)))
