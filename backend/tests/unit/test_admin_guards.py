from __future__ import annotations

import pytest
from litestar.exceptions import NotAuthorizedException

from app.domains.admin.guards import (
    ADMIN_SESSION_COOKIE,
    AdminIdentity,
    create_admin_session,
    decode_admin_session,
    get_admin_identity_from_connection,
)
from app.lib.settings import settings


class DummyConnection:
    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}


def test_create_and_decode_admin_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_secret", "secret")

    token = create_admin_session(
        email="Admin@Example.Com",
        provider="google",
        provider_user_id="abc",
    )
    identity = decode_admin_session(token)
    assert isinstance(identity, AdminIdentity)
    assert identity.email == "admin@example.com"
    assert identity.provider == "google"
    assert identity.provider_user_id == "abc"


def test_get_admin_identity_from_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "secret")

    token = create_admin_session(
        email="admin@example.com",
        provider="google",
        provider_user_id="abc",
    )
    conn = DummyConnection(headers={"authorization": f"Bearer {token}"})
    identity = get_admin_identity_from_connection(conn)
    assert identity.email == "admin@example.com"


def test_get_admin_identity_from_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_secret", "secret")

    token = create_admin_session(
        email="admin@example.com",
        provider="google",
        provider_user_id="abc",
    )
    conn = DummyConnection(cookies={ADMIN_SESSION_COOKIE: token})
    identity = get_admin_identity_from_connection(conn)
    assert identity.email == "admin@example.com"


def test_get_admin_identity_missing_token() -> None:
    with pytest.raises(NotAuthorizedException):
        get_admin_identity_from_connection(DummyConnection())


def test_get_admin_identity_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_secret", "secret")
    conn = DummyConnection(headers={"authorization": "Bearer invalid"})

    with pytest.raises(NotAuthorizedException):
        get_admin_identity_from_connection(conn)
