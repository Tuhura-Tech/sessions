from __future__ import annotations

from dataclasses import dataclass

from litestar import Request
from litestar.exceptions import NotAuthorizedException

from app.db import models as m
from app.domains.caregiver.services.auth import AuthSessionService
from app.domains.caregiver.services.caregiver import CaregiverService
from app.lib.auth import hash_token, utcnow
from app.server.security import SecurityAuditLogger

CAREGIVER_SESSION_COOKIE = "caregiver_session"


@dataclass(frozen=True)
class CaregiverIdentity:
    caregiver_id: str


def _extract_caregiver_token(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth:
        parts = auth.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return request.cookies.get(CAREGIVER_SESSION_COOKIE)


async def get_current_caregiver(
    request: Request,
    auth_session_service: AuthSessionService,
    caregiver_service: CaregiverService,
) -> m.Caregiver:
    token = _extract_caregiver_token(request)
    if not token:
        raise NotAuthorizedException(detail="Caregiver authentication required")

    token_hash = hash_token(token)
    now = utcnow()
    sessions = await auth_session_service.list(
        m.CaregiverSession.token_hash == token_hash,
        m.CaregiverSession.revoked_at.is_(None),
        m.CaregiverSession.expires_at > now,
    )

    if not sessions:
        SecurityAuditLogger.log_authentication_attempt(
            email="unknown",
            method="session-token",
            success=False,
            reason="invalid_or_expired_session",
        )
        raise NotAuthorizedException(detail="Invalid caregiver session")

    session = sessions[0]
    caregiver = await caregiver_service.get(session.caregiver_id)
    if not caregiver:
        SecurityAuditLogger.log_authentication_attempt(
            email="unknown",
            method="session-token",
            success=False,
            reason="caregiver_not_found",
        )
        raise NotAuthorizedException(detail="Invalid caregiver session")

    return caregiver
