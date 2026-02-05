"""Authentication utilities for caregiver magic link authentication."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.lib.settings import settings


def new_token() -> str:
    """Generate a new cryptographically secure random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token using SHA256 with server secret for DB storage.

    Uses server-side secret to mitigate token database leakage.
    """
    h = hashlib.sha256()
    h.update(settings.auth_secret.encode("utf-8"))
    h.update(b"|")
    h.update(token.encode("utf-8"))
    return h.hexdigest()


def utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


def magic_link_expires_at() -> datetime:
    """Calculate expiration time for magic link tokens."""
    return utcnow() + timedelta(minutes=settings.magic_link_ttl_minutes)


def session_expires_at() -> datetime:
    """Calculate expiration time for caregiver sessions."""
    return utcnow() + timedelta(days=settings.caregiver_session_ttl_days)
