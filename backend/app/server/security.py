"""Security middleware for rate limiting, CSRF, and audit logging."""

from __future__ import annotations

import logging
from typing import Any

from litestar.middleware.rate_limit import RateLimitConfig

logger = logging.getLogger("security.audit")


class SecurityAuditLogger:
    """Centralized security audit logging."""

    @staticmethod
    def log_authentication_attempt(
        email: str,
        method: str,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """Log authentication attempt.

        Args:
            email: User email (sanitized)
            method: Authentication method (magic-link, google-oauth)
            success: Whether authentication succeeded
            reason: Failure reason if applicable
        """
        status = "SUCCESS" if success else "FAILURE"
        msg = f"[AUTH-{status}] method={method} email={email}"
        if reason:
            msg += f" reason={reason}"

        if success:
            logger.info(msg)
        else:
            logger.warning(msg)

    @staticmethod
    def log_authorization_attempt(
        user_id: str | None,
        endpoint: str,
        method: str,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """Log authorization attempt.

        Args:
            user_id: User ID (caregiver_id or admin email)
            endpoint: API endpoint
            method: HTTP method
            success: Whether authorization succeeded
            reason: Failure reason if applicable
        """
        status = "ALLOWED" if success else "DENIED"
        user_info = user_id or "anonymous"
        msg = f"[AUTHZ-{status}] endpoint={endpoint} method={method} user={user_info}"
        if reason:
            msg += f" reason={reason}"

        if success:
            logger.info(msg)
        else:
            logger.warning(msg)

    @staticmethod
    def log_admin_action(
        admin_email: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        success: bool = True,
    ) -> None:
        """Log admin actions for audit trail.

        Args:
            admin_email: Admin email address
            action: Action type (create, update, delete)
            resource_type: Resource being modified (caregiver, student, etc)
            resource_id: ID of resource being modified
            success: Whether action succeeded
        """
        status = "SUCCESS" if success else "FAILURE"
        msg = f"[ADMIN-{status}] admin={admin_email} action={action} resource={resource_type}"
        if resource_id:
            msg += f" id={resource_id}"

        if success:
            logger.info(msg)
        else:
            logger.error(msg)

    @staticmethod
    def log_rate_limit_exceeded(
        identifier: str,
        endpoint: str,
        limit: int,
        window: str,
    ) -> None:
        """Log rate limit violations.

        Args:
            identifier: Client identifier (IP, email, etc)
            endpoint: API endpoint
            limit: Rate limit
            window: Time window (e.g., "5/minute")
        """
        logger.warning(
            f"[RATE-LIMIT] identifier={identifier} endpoint={endpoint} "
            f"limit={limit} window={window}"
        )

    @staticmethod
    def log_csrf_attempt(
        identifier: str,
        endpoint: str,
        method: str,
    ) -> None:
        """Log CSRF protection violations.

        Args:
            identifier: Client identifier
            endpoint: API endpoint
            method: HTTP method
        """
        logger.warning(
            f"[CSRF-VIOLATION] identifier={identifier} endpoint={endpoint} method={method}"
        )

    @staticmethod
    def log_suspicious_activity(
        identifier: str,
        activity: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log suspicious or unusual activity.

        Args:
            identifier: Client identifier
            activity: Description of suspicious activity
            details: Additional context
        """
        msg = f"[SUSPICIOUS] identifier={identifier} activity={activity}"
        if details:
            msg += f" details={details}"
        logger.warning(msg)


def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limiting configuration for the application.

    Different endpoints have different rate limits:
    - Authentication endpoints: Stricter limits to prevent brute force
    - Admin endpoints: Moderate limits
    - Public endpoints: Generous limits
    """
    return RateLimitConfig(
        rate_limit=("minute", 60),  # Default: 60 requests per minute
        exclude=[
            "/docs",
            "/openapi",
            "/api/v1/health",
        ],
    )


def get_auth_rate_limit_config() -> RateLimitConfig:
    """Stricter rate limiting for authentication endpoints.

    Prevents brute force and spam attacks on:
    - Magic link generation
    - OAuth flows
    """
    return RateLimitConfig(
        rate_limit=("minute", 5),  # 5 requests per minute per client
    )
