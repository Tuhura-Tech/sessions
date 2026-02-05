from __future__ import annotations

import logging
from typing import Any, Literal
from urllib.parse import urlencode, urlparse

import httpx
from litestar import Controller, Request, Response, get, post
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_200_OK

from app.domains.admin.guards import (
    ADMIN_SESSION_COOKIE,
    create_admin_session,
    get_admin_identity_from_connection,
)
from app.lib.settings import settings
from app.utils.oauth import (
    build_oauth_error_redirect,
    create_oauth_state,
    verify_oauth_state,
)

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _cookie_domain_from_url(url: str) -> str | None:
    host = urlparse(url).hostname
    if not host or host in {"localhost", "127.0.0.1"}:
        return None
    if host.count(".") >= 2:
        return f".{host.split('.', 1)[1]}"
    return None


def _cookie_settings() -> tuple[bool, Literal["lax", "strict", "none"]]:
    scheme = urlparse(settings.admin_base_url).scheme
    secure = scheme == "https"
    samesite: Literal["lax", "strict", "none"] = "none" if secure else "lax"
    return secure, samesite


async def _exchange_code_for_token(code: str, redirect_url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.admin_google_oauth_client_id,
                "client_secret": settings.admin_google_oauth_client_secret,
                "redirect_uri": redirect_url,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        logger.error("Google token exchange failed: %s", response.text)
        raise HTTPException(status_code=500, detail="OAuth token exchange failed")
    return response.json()


async def _fetch_google_userinfo(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        logger.error("Google userinfo fetch failed: %s", response.text)
        raise HTTPException(status_code=500, detail="OAuth userinfo fetch failed")
    return response.json()


class AdminAuthController(Controller):
    """Admin OAuth authentication endpoints."""

    path = "/api/v1/admin/auth"
    tags = ["Admin Auth"]

    @get("/me", status_code=HTTP_200_OK)
    async def me(self, request: Request) -> dict[str, Any]:
        """Check if an admin session is present."""
        try:
            identity = get_admin_identity_from_connection(request)
        except Exception:
            return {"hasSession": False}

        return {
            "hasSession": True,
            "email": identity.email,
            "provider": identity.provider,
        }

    @post("/logout", status_code=HTTP_200_OK)
    async def logout(self) -> Response:
        """Clear admin session cookie."""
        response = Response(content={"ok": True}, status_code=HTTP_200_OK)
        cookie_domain = _cookie_domain_from_url(settings.admin_base_url)
        if cookie_domain:
            response.delete_cookie(ADMIN_SESSION_COOKIE, path="/", domain=cookie_domain)
        else:
            response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
        return response

    @get("/google/start", status_code=HTTP_200_OK, rate_limit=("minute", 10))
    async def google_start(
        self, request: Request, returnTo: str | None = None
    ) -> Response:
        """Start Google OAuth flow for admin login."""
        if (
            not settings.admin_google_oauth_client_id
            or not settings.admin_google_oauth_client_secret
        ):
            raise HTTPException(
                status_code=500, detail="Admin Google OAuth not configured"
            )

        redirect_url = str(request.url_for("admin-google-callback"))
        return_url = returnTo or f"{settings.admin_base_url}/dashboard"
        state = create_oauth_state(
            provider="google",
            redirect_url=return_url,
            secret_key=settings.auth_secret,
            action="admin-login",
        )

        params = {
            "client_id": settings.admin_google_oauth_client_id,
            "redirect_uri": redirect_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return Response(content=None, status_code=302, headers={"Location": auth_url})

    @get("/google/callback", name="admin-google-callback")
    async def google_callback(
        self,
        request: Request,
        code: str | None = None,
        error: str | None = None,
    ) -> Response:
        """Handle Google OAuth callback, create admin session, and redirect."""
        fallback_redirect = f"{settings.admin_base_url}/login"

        # Get state from query parameters (Google sends it as 'state')
        state_param = request.query_params.get("state")

        if error:
            redirect = build_oauth_error_redirect(
                fallback_redirect, "oauth_error", error
            )
            return Response(
                content=None, status_code=302, headers={"Location": redirect}
            )

        if not code or not state_param:
            redirect = build_oauth_error_redirect(
                fallback_redirect, "oauth_error", "Missing OAuth parameters"
            )
            return Response(
                content=None, status_code=302, headers={"Location": redirect}
            )

        valid, payload, message = verify_oauth_state(
            state=state_param,
            expected_provider="google",
            secret_key=settings.auth_secret,
        )
        if not valid:
            redirect = build_oauth_error_redirect(
                fallback_redirect, "oauth_error", message
            )
            return Response(
                content=None, status_code=302, headers={"Location": redirect}
            )

        redirect_url = str(request.url_for("admin-google-callback"))
        return_to = str(payload.get("redirect_url") or fallback_redirect)

        token_data = await _exchange_code_for_token(code, redirect_url)
        access_token = str(token_data.get("access_token") or "")
        if not access_token:
            redirect = build_oauth_error_redirect(
                return_to, "oauth_error", "Missing access token"
            )
            return Response(
                content=None, status_code=302, headers={"Location": redirect}
            )

        userinfo = await _fetch_google_userinfo(access_token)
        email = str(userinfo.get("email") or "").strip().lower()
        provider_user_id = str(userinfo.get("sub") or "").strip()
        if not email or not provider_user_id:
            redirect = build_oauth_error_redirect(
                return_to, "oauth_error", "Missing user info"
            )
            return Response(
                content=None, status_code=302, headers={"Location": redirect}
            )

        session_token = create_admin_session(
            email=email,
            provider="google",
            provider_user_id=provider_user_id,
        )

        response = Response(
            content=None, status_code=302, headers={"Location": return_to}
        )
        secure, samesite = _cookie_settings()
        cookie_domain = _cookie_domain_from_url(settings.admin_base_url)
        response.set_cookie(
            ADMIN_SESSION_COOKIE,
            session_token,
            domain=cookie_domain,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path="/",
        )
        return response
