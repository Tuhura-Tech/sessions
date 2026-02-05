"""Rate limiting middleware to prevent abuse.

Implements rate limiting for general API endpoints and strict limits for
sensitive operations like magic link generation.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from litestar.exceptions import TooManyRequestsException
from litestar.types import Receive, Scope, Send

from app.lib.settings import settings

logger = logging.getLogger(__name__)

# Store rate limit counts in memory (in production, use Redis)
# Structure: {ip_address: {endpoint: [(timestamp, count), ...]}}
_rate_limit_store: dict[str, dict[str, list[tuple[datetime, int]]]] = defaultdict(
    lambda: defaultdict(list)
)


def get_client_ip(scope: Scope) -> str:
    """Extract client IP from ASGI scope.

    Args:
        scope: The ASGI scope

    Returns:
        The client's IP address
    """
    if scope["type"] != "http":
        return "unknown"

    # Check X-Forwarded-For header first (for proxied requests)
    headers = dict(scope.get("headers", []))
    if b"x-forwarded-for" in headers:
        forwarded = headers[b"x-forwarded-for"].decode()
        # Get first IP in the chain
        return forwarded.split(",")[0].strip()

    # Fall back to client info
    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"


def check_rate_limit(
    client_ip: str,
    endpoint: str,
    requests_per_minute: int,
    requests_per_hour: int | None = None,
) -> bool:
    """Check if a client has exceeded rate limits.

    Args:
        client_ip: The client IP address
        endpoint: The endpoint identifier (e.g., "/api/v1/auth/magic-link")
        requests_per_minute: Max requests allowed per minute
        requests_per_hour: Max requests allowed per hour (optional)

    Returns:
        True if within limits, False if rate limit exceeded

    Raises:
        TooManyRequestsException: If rate limit exceeded
    """
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    hour_ago = now - timedelta(hours=1)

    client_limits = _rate_limit_store[client_ip][endpoint]

    # Clean old entries
    client_limits[:] = [(ts, count) for ts, count in client_limits if ts > hour_ago]

    # Count requests in last minute
    minute_requests = sum(count for ts, count in client_limits if ts > minute_ago)

    if minute_requests >= requests_per_minute:
        raise TooManyRequestsException(
            detail=f"Rate limit exceeded: max {requests_per_minute} requests per minute"
        )

    # Count requests in last hour if specified
    if requests_per_hour is not None:
        hour_requests = sum(count for ts, count in client_limits)
        if hour_requests >= requests_per_hour:
            raise TooManyRequestsException(
                detail=f"Rate limit exceeded: max {requests_per_hour} requests per hour"
            )

    # Record this request
    client_limits.append((now, 1))

    return True


class RateLimitMiddleware:
    """Middleware for enforcing rate limits on API endpoints."""

    # Endpoints with special rate limits
    STRICT_LIMIT_ENDPOINTS = {
        "/api/v1/auth/caregiver/login": (3, 10),  # 3 per minute, 10 per hour
        "/api/v1/auth/caregiver/verify": (5, 20),  # 5 per minute, 20 per hour
        "/api/v1/admin/auth/google/start": (10, 50),  # Admin endpoints less strict
    }

    # Rate limits for resource-intensive operations
    CSV_EXPORT_RATE_LIMIT = (5, 20)  # 5 per minute, 20 per hour for CSV exports

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process incoming request for rate limiting.

        Args:
            scope: The ASGI scope
            receive: The ASGI receive callable
            send: The ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # If in debug mode, skip rate limiting
        if settings.debug:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "").upper()

        # Only apply rate limiting to certain methods
        if method not in ("GET", "POST", "PUT", "DELETE"):
            await self.app(scope, receive, send)
            return

        # Get client IP
        client_ip = get_client_ip(scope)

        # Determine rate limits for this endpoint
        if path in self.STRICT_LIMIT_ENDPOINTS:
            per_minute, per_hour = self.STRICT_LIMIT_ENDPOINTS[path]
        # Apply stricter limits to CSV export endpoints
        elif "/export/" in path and path.endswith(".csv"):
            per_minute, per_hour = self.CSV_EXPORT_RATE_LIMIT
        else:
            per_minute = settings.rate_limit_requests_per_minute
            per_hour = None

        # Check rate limit
        try:
            check_rate_limit(client_ip, path, per_minute, per_hour)
        except TooManyRequestsException as e:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "endpoint": path,
                    "reason": str(e),
                },
            )
            raise

        # Continue with request
        await self.app(scope, receive, send)
