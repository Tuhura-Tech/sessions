"""
Unit tests for authentication utilities in app/lib/auth.py

Tests token generation, hashing, and expiration calculations.
These tests are fast and isolated - no database needed.
"""

import pytest
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from app.lib.auth import (
    new_token,
    hash_token,
    utcnow,
    magic_link_expires_at,
    session_expires_at,
)
from app.lib.settings import settings

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.auth
class TestTokenGeneration:
    """Test secure token generation."""

    def test_new_token_returns_string(self):
        """Test that new_token returns a non-empty string."""
        token = new_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_new_token_is_unique(self):
        """Test that new_token generates unique tokens."""
        token1 = new_token()
        token2 = new_token()
        assert token1 != token2

    def test_new_token_is_long_enough(self):
        """Test that new_token generates sufficiently long tokens."""
        # token_urlsafe(32) produces ~43 characters
        token = new_token()
        assert len(token) >= 40  # Base64 encoded minimum

    def test_new_token_is_url_safe(self):
        """Test that new_token generates URL-safe characters."""
        token = new_token()
        # URL-safe characters: A-Z a-z 0-9 - _
        # Should not contain / + = or other special chars
        assert all(c.isalnum() or c in "-_" for c in token)


@pytest.mark.unit
@pytest.mark.auth
class TestTokenHashing:
    """Test token hashing for secure storage."""

    def test_hash_token_returns_string(self):
        """Test that hash_token returns a non-empty string."""
        token = new_token()
        hashed = hash_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_token_is_deterministic(self):
        """Test that hashing the same token always produces the same hash."""
        token = new_token()
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_is_not_reversible(self):
        """Test that hashed tokens cannot be reversed to get original."""
        token = new_token()
        hashed = hash_token(token)
        # The hash should not contain the original token
        assert token not in hashed

    def test_hash_token_different_tokens_different_hashes(self):
        """Test that different tokens produce different hashes."""
        token1 = new_token()
        token2 = new_token()
        hash1 = hash_token(token1)
        hash2 = hash_token(token2)
        assert hash1 != hash2

    def test_hash_token_uses_sha256(self):
        """Test that hash_token uses SHA256 algorithm."""
        token = new_token()
        hashed = hash_token(token)
        # SHA256 produces 64-character hex string
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_incorporates_secret(self):
        """Test that hash uses the server secret."""
        token = new_token()
        hashed1 = hash_token(token)

        # The hash should be different if we hash with different server secret
        # (we can't actually change the secret, but we can verify the format)
        h = sha256()
        h.update(settings.auth_secret.encode("utf-8"))
        h.update(b"|")
        h.update(token.encode("utf-8"))
        expected_hash = h.hexdigest()
        assert hashed1 == expected_hash


@pytest.mark.unit
@pytest.mark.auth
class TestTimeUtilities:
    """Test time and expiration utilities."""

    def test_utcnow_returns_datetime(self):
        """Test that utcnow returns a datetime object."""
        now = utcnow()
        assert isinstance(now, datetime)

    def test_utcnow_is_utc(self):
        """Test that utcnow returns UTC timezone-aware datetime."""
        now = utcnow()
        assert now.tzinfo is not None
        assert now.tzinfo.tzname(now) == "UTC"

    def test_utcnow_is_recent(self):
        """Test that utcnow returns current time (within 1 second)."""
        before = datetime.now(timezone.utc)
        now = utcnow()
        after = datetime.now(timezone.utc)
        assert before <= now <= after

    def test_magic_link_expires_at_returns_datetime(self):
        """Test that magic_link_expires_at returns a datetime."""
        expires = magic_link_expires_at()
        assert isinstance(expires, datetime)

    def test_magic_link_expires_at_is_in_future(self):
        """Test that magic_link_expires_at returns a future time."""
        before = utcnow()
        expires = magic_link_expires_at()
        assert expires > before

    def test_magic_link_expires_at_uses_configured_ttl(self):
        """Test that magic_link_expires_at uses settings.magic_link_ttl_minutes."""
        before = utcnow()
        expires = magic_link_expires_at()

        # Should be approximately settings.magic_link_ttl_minutes in the future
        expected_ttl = timedelta(minutes=settings.magic_link_ttl_minutes)

        # Allow 1 second margin for execution time
        assert expires > before + expected_ttl - timedelta(seconds=1)
        assert expires < before + expected_ttl + timedelta(seconds=5)

    def test_session_expires_at_returns_datetime(self):
        """Test that session_expires_at returns a datetime."""
        expires = session_expires_at()
        assert isinstance(expires, datetime)

    def test_session_expires_at_is_in_future(self):
        """Test that session_expires_at returns a future time."""
        before = utcnow()
        expires = session_expires_at()
        assert expires > before

    def test_session_expires_at_uses_configured_ttl(self):
        """Test that session_expires_at uses settings.caregiver_session_ttl_days."""
        before = utcnow()
        expires = session_expires_at()

        # Should be approximately settings.caregiver_session_ttl_days in the future
        expected_ttl = timedelta(days=settings.caregiver_session_ttl_days)

        # Allow 1 second margin for execution time
        assert expires > before + expected_ttl - timedelta(seconds=1)
        assert expires < before + expected_ttl + timedelta(seconds=5)

    def test_session_ttl_much_longer_than_magic_link_ttl(self):
        """Test that session TTL is much longer than magic link TTL."""
        magic_expires = magic_link_expires_at()
        session_expires = session_expires_at()

        # Session should be valid much longer than magic link
        # Magic links typically 15 min, sessions typically 30 days
        assert session_expires > magic_expires

        # Rough check: session should be at least 10 days longer
        diff = session_expires - magic_expires
        assert diff > timedelta(days=10)


@pytest.mark.unit
@pytest.mark.auth
class TestTokenIntegration:
    """Test interactions between token generation and hashing."""

    def test_generate_and_hash_workflow(self):
        """Test the typical workflow: generate token, hash it for storage."""
        # Generate a token (sent to user)
        token = new_token()
        assert isinstance(token, str)
        assert len(token) > 0

        # Hash it for storage in database
        hashed = hash_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64

        # Token and hash should be different
        assert token != hashed

        # Hash should be consistent
        assert hash_token(token) == hashed

    def test_expiration_workflow(self):
        """Test the typical workflow: generate token and set expiration."""
        new_token()
        expires = magic_link_expires_at()

        now = utcnow()
        assert expires > now

        # Should be valid for configured TTL minutes
        ttl_seconds = settings.magic_link_ttl_minutes * 60
        expected_min = now + timedelta(seconds=ttl_seconds - 1)
        expected_max = now + timedelta(seconds=ttl_seconds + 5)

        assert expected_min <= expires <= expected_max

    def test_token_validation_scenario(self):
        """Test realistic token validation scenario."""
        # Scenario: User requests magic link, server generates and hashes token
        user_token = new_token()
        token_hash = hash_token(user_token)
        expires_at = magic_link_expires_at()

        # Store token_hash and expires_at in database
        # (simulated - no actual database here)
        stored_token_hash = token_hash
        stored_expires_at = expires_at

        # Later: User receives token and clicks link with it
        incoming_token = user_token  # In real scenario, from request
        current_time = utcnow()

        # Verify: hash the incoming token and compare
        incoming_hash = hash_token(incoming_token)
        is_valid_hash = incoming_hash == stored_token_hash
        is_not_expired = current_time < stored_expires_at

        assert is_valid_hash is True
        assert is_not_expired is True

        # Try with different token
        different_token = new_token()
        different_hash = hash_token(different_token)
        is_valid_different = different_hash == stored_token_hash
        assert is_valid_different is False
