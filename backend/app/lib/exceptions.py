"""Litestar-saqlalchemy exception types.

Also, defines functions that translate service and repository exceptions
into HTTP exceptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from advanced_alchemy.exceptions import (
    DuplicateKeyError,
    IntegrityError,
    NotFoundError as AlchemyNotFoundError,
)
from litestar.exceptions import (
    ClientException,
    HTTPException,
    InternalServerException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.exceptions.responses import (
    create_debug_response as _create_debug_response,  # pyright: ignore[reportUnknownVariableType]
)
from litestar.exceptions.responses import (
    create_exception_response as _create_exception_response,  # pyright: ignore[reportUnknownVariableType]
)
from litestar.repository.exceptions import ConflictError, NotFoundError, RepositoryError
from litestar.status_codes import HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
# from structlog.contextvars import bind_contextvars

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.connection import Request
    from litestar.response import Response
    from litestar.types import Scope

__all__ = (
    "ApplicationError",
    "AuthorizationError",
    "HealthCheckConfigurationError",
    "after_exception_hook_handler",
)


class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""

    detail: str

    def __init__(self, *args: Any, detail: str = "") -> None:
        """Initialize ``AdvancedAlchemyException``.

        Args:
            *args: args are converted to :class:`str` before passing to :class:`Exception`
            detail: detail of the exception.
        """
        str_args = [str(arg) for arg in args if arg]
        if not detail:
            if str_args:
                detail, *str_args = str_args
            elif hasattr(self, "detail"):
                detail = self.detail
        self.detail = detail
        super().__init__(*str_args)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join((*self.args, self.detail)).strip()


class MissingDependencyError(ApplicationError, ImportError):
    """Missing optional dependency.

    This exception is raised only when a module depends on a dependency that has not been installed.
    """


class ApplicationClientError(ApplicationError):
    """Base exception type for client errors."""


class AuthorizationError(ApplicationClientError):
    """A user tried to do something they shouldn't have."""


class HealthCheckConfigurationError(ApplicationError):
    """An error occurred while registering an health check."""


class _HTTPConflictException(HTTPException):
    """Request conflict with the current state of the target resource."""

    status_code = HTTP_409_CONFLICT


def after_exception_hook_handler(exc: Exception, _scope: Scope) -> None:
    """Log exceptions after they are handled by Litestar.

    4xx client errors are logged at WARNING level without a stack trace.
    5xx server errors are logged at ERROR level with full exc_info.

    Args:
        exc: the exception that was raised.
        _scope: scope of the request
    """
    import logging

    _logger = logging.getLogger("litestar.exceptions")

    if isinstance(exc, ApplicationError):
        return
    if isinstance(exc, HTTPException):
        if exc.status_code < HTTP_500_INTERNAL_SERVER_ERROR:
            _logger.warning(
                "HTTP %s: %s",
                exc.status_code,
                getattr(exc, "detail", str(exc)),
            )
        else:
            _logger.error(
                "HTTP %s: %s",
                exc.status_code,
                getattr(exc, "detail", str(exc)),
                exc_info=exc,
            )
        return
    _logger.error("Unhandled exception", exc_info=exc)


_create_debug_response_typed = cast(
    "Callable[[Any, Exception], Any]", _create_debug_response
)
_create_exception_response_typed = cast(
    "Callable[[Any, HTTPException], Any]", _create_exception_response
)


def create_debug_response(
    request: Request[Any, Any, Any], exc: Exception
) -> Response[Any]:
    return cast("Response[Any]", _create_debug_response_typed(request, exc))


def create_exception_response(
    request: Request[Any, Any, Any], exc: HTTPException
) -> Response[Any]:
    return cast("Response[Any]", _create_exception_response_typed(request, exc))


def exception_to_http_response(
    request: Request[Any, Any, Any],
    exc: ApplicationError | RepositoryError | AlchemyNotFoundError,
) -> Response[Any]:
    """Transform repository exceptions to HTTP exceptions.

    Args:
        request: The request that experienced the exception.
        exc: Exception raised during handling of the request.

    Returns:
        Exception response appropriate to the type of original exception.
    """
    http_exc: type[HTTPException]
    if isinstance(exc, (NotFoundError, AlchemyNotFoundError)):
        http_exc = NotFoundException
    elif isinstance(
        exc, ConflictError | RepositoryError | IntegrityError | DuplicateKeyError
    ):
        http_exc = _HTTPConflictException
    elif isinstance(exc, AuthorizationError):
        http_exc = PermissionDeniedException
    elif isinstance(exc, ApplicationClientError):
        http_exc = ClientException
    else:
        http_exc = InternalServerException
    if request.app.debug and http_exc not in {
        PermissionDeniedException,
        NotFoundError,
        AuthorizationError,
    }:
        return create_debug_response(request, exc)
    detail = getattr(exc, "detail", "") or (
        str(exc.__cause__) if exc.__cause__ else str(exc)
    )
    return create_exception_response(request, http_exc(detail=detail))
