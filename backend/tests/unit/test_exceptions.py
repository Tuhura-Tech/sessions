from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from advanced_alchemy.exceptions import DuplicateKeyError, IntegrityError
from litestar.exceptions import (
    ClientException,
    InternalServerException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.repository.exceptions import ConflictError, NotFoundError

from app.lib.exceptions import (
    ApplicationClientError,
    ApplicationError,
    AuthorizationError,
    exception_to_http_response,
)

if TYPE_CHECKING:
    from litestar import Request


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock()
    request.app.debug = False
    request.url_for = MagicMock(return_value="http://localhost")
    request.route_handler = MagicMock()
    request.route_handler.type_encoders = None
    return request


def test_application_error() -> None:
    exc = ApplicationError("test detail")
    assert exc.detail == "test detail"
    assert "ApplicationError - test detail" in repr(exc)


def test_authorization_error() -> None:
    exc = AuthorizationError(detail="forbidden")
    assert exc.detail == "forbidden"


def test_exception_to_http_response_not_found(mock_request: Request) -> None:
    exc = NotFoundError(detail="Entity not found")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == NotFoundException.status_code


def test_exception_to_http_response_conflict(mock_request: Request) -> None:
    exc = ConflictError(detail="Conflict")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == 409


def test_exception_to_http_response_duplicate_key(mock_request: Request) -> None:
    exc = DuplicateKeyError(detail="Duplicate")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == 409


def test_exception_to_http_response_integrity_error(mock_request: Request) -> None:
    exc = IntegrityError(detail="Integrity violation")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == 409


def test_exception_to_http_response_authorization_error(
    mock_request: Request,
) -> None:
    exc = AuthorizationError(detail="Forbidden")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == PermissionDeniedException.status_code


def test_exception_to_http_response_application_client_error(
    mock_request: Request,
) -> None:
    exc = ApplicationClientError(detail="Client error")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == ClientException.status_code


def test_exception_to_http_response_internal_server_error(
    mock_request: Request,
) -> None:
    exc = ApplicationError(detail="Unexpected error")
    response = exception_to_http_response(mock_request, exc)
    assert response.status_code == InternalServerException.status_code


def test_exception_to_http_response_debug_mode(mock_request: Request) -> None:
    mock_request.app.debug = True
    exc = ConflictError(detail="Conflict in debug")
    response = exception_to_http_response(mock_request, exc)
    # Debug mode returns debug response with extra info
    assert response.status_code == 500
