from __future__ import annotations

import logging

from litestar import Controller, get, post, Request, Response
from litestar.status_codes import HTTP_200_OK

from app.domains.caregiver.schemas.auth import (
    MagicLinkRequest,
    MagicLinkRequestResponse,
)
from app.db import models as m
from app.domains.caregiver.services.auth import AuthMagicLinkService, AuthSessionService
from app.domains.caregiver.services.caregiver import CaregiverService
from app.lib.auth import (
    hash_token,
    magic_link_expires_at,
    new_token,
    session_expires_at,
    utcnow,
)
from app.lib.settings import settings
from app.server.security import SecurityAuditLogger
from advanced_alchemy.extensions.litestar import providers

logger = logging.getLogger(__name__)

CAREGIVER_SESSION_COOKIE = "caregiver_session"


def _safe_return_to(value: str | None) -> str:
    """Only allow relative paths to avoid open redirects."""
    if not value:
        return "/account"
    if value.startswith("/") and not value.startswith("//") and ":" not in value:
        return value
    return "/account"


class CaregiverAuthController(Controller):
    """Caregiver authentication endpoints (magic-link)."""

    path = "/api/v1/auth"
    tags = ["Caregiver Auth"]
    dependencies = providers.create_service_dependencies(
        AuthMagicLinkService,
        "auth_magic_link_service",
    )
    dependencies.update(
        providers.create_service_dependencies(
            AuthSessionService,
            "auth_session_service",
        )
    )
    dependencies.update(
        providers.create_service_dependencies(
            CaregiverService,
            "caregiver_service",
        )
    )

    @post(
        "/magic-link",
        status_code=HTTP_200_OK,
        summary="Request magic link",
        rate_limit=("minute", 5),  # 5 requests per minute per client
    )
    async def request_magic_link(
        self,
        auth_magic_link_service: AuthMagicLinkService,
        caregiver_service: CaregiverService,
        data: MagicLinkRequest,
    ) -> MagicLinkRequestResponse:
        """Send a passwordless magic link to a caregiver email.

        Creates account if needed and reuses unexpired links to throttle requests.
        In debug mode, returns the token for local testing (no email sent).
        """
        email = data.email.lower().strip()
        return_to = _safe_return_to(data.return_to)

        # Find or create caregiver account
        caregivers = await caregiver_service.list(m.Caregiver.email == email)
        if caregivers:
            caregiver = caregivers[0]
        else:
            caregiver = await caregiver_service.create({"email": email})
            logger.info(f"Created new caregiver account: {email}")

        # Throttle: re-use recent unexpired link if one exists
        now = utcnow()
        existing_links = await auth_magic_link_service.list(
            m.CaregiverMagicLink.caregiver_id == caregiver.id,
            m.CaregiverMagicLink.used_at.is_(None),
            m.CaregiverMagicLink.expires_at > now,
        )

        if existing_links:
            # Reuse existing link
            raw_token = None  # Can't reconstruct from hash
            logger.info(f"Reusing existing magic link for {email}")
        else:
            # Create new magic link
            raw_token = new_token()
            token_hash = hash_token(raw_token)
            await auth_magic_link_service.create(
                {
                    "caregiver_id": caregiver.id,
                    "token_hash": token_hash,
                    "expires_at": magic_link_expires_at(),
                }
            )
            logger.info(f"Created new magic link for {email}")

        # Generate a new token if we're reusing (can't reconstruct the old one)
        if raw_token is None:
            raw_token = new_token()
            token_hash = hash_token(raw_token)
            await auth_magic_link_service.create(
                {
                    "caregiver_id": caregiver.id,
                    "token_hash": token_hash,
                    "expires_at": magic_link_expires_at(),
                }
            )

        # In debug mode, log the token to console instead of sending email
        if settings.debug:
            consume_url = (
                f"{settings.public_base_url}/api/v1/auth/magic-link/consume"
                f"?token={raw_token}&returnTo={return_to}"
            )
            logger.warning("=" * 80)
            logger.warning(f"🔐 DEBUG: Magic Link for {email}")
            logger.warning(f"Token: {raw_token}")
            logger.warning(f"Consume URL: {consume_url}")
            logger.warning("=" * 80)
            print("\n" + "=" * 80)
            print(f"🔐 DEBUG: Magic Link for {email}")
            print(f"Token: {raw_token}")
            print(f"Consume URL: {consume_url}")
            print("=" * 80 + "\n")

        return MagicLinkRequestResponse(
            ok=True, debug_token=raw_token if settings.debug else None
        )

    @get("/magic-link/consume", summary="Consume magic link")
    async def consume_magic_link(
        self,
        auth_magic_link_service: AuthMagicLinkService,
        auth_session_service: AuthSessionService,
        caregiver_service: CaregiverService,
        token: str,
        returnTo: str | None = None,
    ) -> Response:
        """Consume a magic link, mark it used, create session, and redirect."""
        safe_return_to = _safe_return_to(returnTo)
        token_hash = hash_token(token)
        now = utcnow()

        # Find the magic link
        magic_links = await auth_magic_link_service.list(
            m.CaregiverMagicLink.token_hash == token_hash,
            m.CaregiverMagicLink.used_at.is_(None),
            m.CaregiverMagicLink.expires_at > now,
        )

        if not magic_links:
            SecurityAuditLogger.log_authentication_attempt(
                email="unknown",
                method="magic-link",
                success=False,
                reason="invalid_or_expired_token",
            )
            return Response(
                content={"ok": False, "error": "Invalid or expired link"},
                status_code=400,
            )

        link = magic_links[0]
        # Fetch caregiver by ID
        caregiver = await caregiver_service.get(link.caregiver_id)
        if not caregiver:
            SecurityAuditLogger.log_authentication_attempt(
                email="unknown",
                method="magic-link",
                success=False,
                reason="caregiver_not_found",
            )
            return Response(
                content={"ok": False, "error": "Invalid link"}, status_code=400
            )

        # Mark link as used and update caregiver
        await auth_magic_link_service.update(
            {"used_at": now},
            link.id,
            auto_commit=True,
        )
        await caregiver_service.update(
            {
                "email_verified": True,
                "last_login_at": now,
            },
            caregiver.id,
            auto_commit=True,
        )

        # Log successful authentication
        SecurityAuditLogger.log_authentication_attempt(
            email=caregiver.email,
            method="magic-link",
            success=True,
        )

        # Create session
        raw_session_token = new_token()
        await auth_session_service.create(
            {
                "caregiver_id": caregiver.id,
                "token_hash": hash_token(raw_session_token),
                "expires_at": session_expires_at(),
            },
            auto_commit=True,
        )

        logger.info(f"Caregiver {caregiver.email} logged in successfully")

        # Redirect back to frontend
        location = f"{settings.frontend_base_url}{safe_return_to}"
        response = Response(
            content=None, status_code=302, headers={"Location": location}
        )

        # Set secure session cookie
        cookie_domain = ".tuhuratech.org.nz"
        response.set_cookie(
            CAREGIVER_SESSION_COOKIE,
            raw_session_token,
            domain=cookie_domain if not settings.debug else None,
            httponly=True,
            secure=not settings.debug,  # Allow http in debug mode
            samesite="none" if not settings.debug else "lax",
            path="/",
        )

        return response

    @post("/logout", status_code=HTTP_200_OK, summary="Log out")
    async def logout(
        self, auth_session_service: AuthSessionService, request: Request
    ) -> Response:
        """Revoke the caregiver session and clear the session cookie (idempotent)."""
        raw = request.cookies.get(CAREGIVER_SESSION_COOKIE)
        if raw:
            token_hash = hash_token(raw)
            now = utcnow()

            sessions = await auth_session_service.list(
                m.CaregiverSession.token_hash == token_hash,
            )
            if sessions:
                session = sessions[0]
                if session.revoked_at is None:
                    await auth_session_service.update({"revoked_at": now}, session.id)
                    logger.info(f"Caregiver logged out: {session.caregiver_id}")

        response = Response(content={"ok": True}, status_code=HTTP_200_OK)
        response.delete_cookie(CAREGIVER_SESSION_COOKIE, path="/")
        return response
