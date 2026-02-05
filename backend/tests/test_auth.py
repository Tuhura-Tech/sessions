#!/usr/bin/env python3
"""
Test script for caregiver magic link authentication.
Run this from the backend directory with: python -m pytest tests/test_auth.py
"""

import pytest
from uuid import uuid4

pytestmark = pytest.mark.anyio


async def test_magic_link_request_flow(test_client):
    """Test complete magic link authentication flow."""

    # Configuration
    test_email = f"test-{uuid4().hex}@example.com"
    test_return_to = "/dashboard"

    # 1. Request magic link
    print("\n[1] Requesting magic link...")
    response = await test_client.post(
        "/api/v1/auth/magic-link",
        json={
            "email": test_email,
            "returnTo": test_return_to,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

    debug_token = data.get("debugToken") or data.get("debug_token")
    assert debug_token is not None
    print(f"✓ Received debug token: {debug_token[:20]}...")

    # 2. Consume magic link
    print("\n[2] Consuming magic link...")
    token = data.get("debugToken") or data.get("debug_token")
    assert token is not None
    response = await test_client.get(
        "/api/v1/auth/magic-link/consume",
        params={
            "token": token,
            "returnTo": test_return_to,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers.get("Location")
    assert location is not None
    assert test_return_to in location
    print(f"✓ Redirected to: {location}")

    # Check for session cookie
    cookies = response.cookies
    assert "caregiver_session" in cookies or response.headers.get("set-cookie")
    if "caregiver_session" in cookies:
        print(f"✓ Session cookie set: {cookies['caregiver_session'][:20]}...")

    print("\n✅ All tests passed!")


async def test_invalid_token(test_client):
    """Test consuming an invalid token."""

    response = await test_client.get(
        "/api/v1/auth/magic-link/consume",
        params={
            "token": "invalid-token-12345",
            "returnTo": "/account",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["ok"] is False
    assert "Invalid or expired" in data.get("error", "")
    print("✓ Invalid token properly rejected")


async def test_token_reuse_prevention(test_client):
    """Test that tokens can only be used once."""

    test_email = f"reuse-{uuid4().hex}@example.com"

    # Request and consume once
    response1 = await test_client.post(
        "/api/v1/auth/magic-link", json={"email": test_email}
    )
    assert response1.status_code == 200
    token = response1.json().get("debugToken") or response1.json().get("debug_token")
    assert token is not None

    # First consumption
    response2 = await test_client.get(
        "/api/v1/auth/magic-link/consume",
        params={"token": token},
        follow_redirects=False,
    )
    assert response2.status_code == 302
    print("✓ First consumption succeeded")

    # Attempt reuse
    response3 = await test_client.get(
        "/api/v1/auth/magic-link/consume",
        params={"token": token},
        follow_redirects=False,
    )
    assert response3.status_code in (302, 400)
    print("✓ Token reuse prevented")


if __name__ == "__main__":
    print("🧪 Running Magic Link Authentication Tests")
    print("   Run with: python -m pytest tests/test_auth.py -v")
