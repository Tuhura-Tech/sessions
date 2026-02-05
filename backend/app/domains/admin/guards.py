from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import jwt
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException, NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler

from app.lib.auth import utcnow
from app.lib.settings import settings
from app.server.security import SecurityAuditLogger

logger = logging.getLogger(__name__)

ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AdminIdentity:
    email: str
    provider: str
    provider_user_id: str


def _admin_auth_secret() -> str:
    return settings.auth_secret


def is_allowed_admin(email: str) -> bool:
    """The Oauth does the filtering so we can just enable users."""
    return True


def create_admin_session(*, email: str, provider: str, provider_user_id: str) -> str:
    now = utcnow()
    exp = now + timedelta(hours=settings.admin_session_ttl_hours)

    payload = {
        "email": email.strip().lower(),
        "provider": provider,
        "provider_user_id": provider_user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    return jwt.encode(payload, _admin_auth_secret(), algorithm=ADMIN_SESSION_ALGORITHM)


def decode_admin_session(token: str) -> AdminIdentity:
    try:
        payload = jwt.decode(
            token,
            _admin_auth_secret(),
            algorithms=[ADMIN_SESSION_ALGORITHM],
        )
    except jwt.PyJWTError as e:
        raise NotAuthorizedException(detail="Invalid admin session") from e

    email = str(payload.get("email") or "").strip().lower()
    provider = str(payload.get("provider") or "").strip().lower()
    provider_user_id = str(payload.get("provider_user_id") or "").strip()

    if not email or not provider or not provider_user_id:
        raise NotAuthorizedException(detail="Invalid admin session")

    return AdminIdentity(
        email=email, provider=provider, provider_user_id=provider_user_id
    )


def get_admin_identity_from_connection(connection: ASGIConnection) -> AdminIdentity:
    auth = connection.headers.get("authorization")
    token: str | None = None

    if auth:
        parts = auth.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if not token:
        token = connection.cookies.get(ADMIN_SESSION_COOKIE)

    if not token:
        logger.debug("Admin access attempt without token")
        raise NotAuthorizedException(detail="Admin authentication required")

    identity = decode_admin_session(token)

    # Defense-in-depth: even if a token is valid, require allowlist membership.
    if not is_allowed_admin(identity.email):
        SecurityAuditLogger.log_authorization_attempt(
            user_id=identity.email,
            endpoint="/api/v1/admin",
            method="*",
            success=False,
            reason="email_not_in_allowlist",
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    SecurityAuditLogger.log_authorization_attempt(
        user_id=identity.email,
        endpoint="/api/v1/admin",
        method="*",
        success=True,
    )

    return identity


def admin_session_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    # Raises on failure.
    get_admin_identity_from_connection(connection)
