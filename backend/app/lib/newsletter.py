"""Newsletter integration.

This module contains functionality to notify Ghost about a user's newsletter subscription.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
import jwt

from app.lib.settings import settings

logger = logging.getLogger(__name__)


def _create_ghost_token(api_key: str) -> str:
    """Create a Ghost Admin API JWT token.

    Args:
        api_key: Ghost Admin API key in format "id:secret"

    Returns:
        JWT token for Ghost API authentication
    """
    # Split the key into ID and SECRET
    key_id, secret = api_key.split(":")

    # Prepare header and payload
    iat = int(datetime.now().timestamp())

    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"}

    # Create the token (decode secret from hex)
    token = jwt.encode(
        payload, bytes.fromhex(secret), algorithm="HS256", headers=header
    )

    return token


async def notify_newsletter_subscription(
    *, email: str, name: str | None = None
) -> None:
    """Notify an external newsletter system about an opt-in.

    If `settings.newsletter_webhook_url` is not configured, this function is a no-op.
    """
    if not settings.newsletter_webhook_url:
        logger.info("Newsletter webhook not configured; skipping opt-in for %s", email)
        return

    # Build member payload
    member = {
        "email": email,
        "labels": [{"name": "Session", "slug": "session"}],
    }
    if name:
        member["name"] = name

    payload = {"members": [member]}

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "TuhuraSessions/1.0 (+https://tuhuratech.org.nz)",
    }
    token = (settings.newsletter_webhook_token or "").strip()
    if token:
        try:
            ghost_token = _create_ghost_token(token)
            headers["Authorization"] = f"Ghost {ghost_token}"
        except Exception as e:
            logger.error(f"Failed to create Ghost token: {e}")
            return

    if settings.email_dry_run:
        logger.info("DRY RUN - Would POST newsletter opt-in with payload: %s", payload)
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        path = f"{settings.newsletter_webhook_url}/ghost/api/admin/members/"
        try:
            resp = await client.post(path, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info(f"Successfully subscribed {email} to newsletter")
        except httpx.HTTPStatusError as e:
            # 422 means member already exists, which is fine
            if e.response.status_code == 422 and "already exists" in e.response.text.lower():
                logger.info(f"Member {email} already subscribed to newsletter")
            else:
                logger.error(
                    f"Newsletter subscription failed for {email}: {e.response.status_code} - {e.response.text}"
                )
        except Exception as e:
            logger.error(f"Newsletter subscription failed for {email}: {e}")
