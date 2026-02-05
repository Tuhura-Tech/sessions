from __future__ import annotations

import time

import jwt

from app.utils.oauth import (
    build_oauth_error_redirect,
    create_oauth_state,
    verify_oauth_state,
)


def test_create_oauth_state() -> None:
    state = create_oauth_state(
        provider="google",
        redirect_url="http://localhost/callback",
        secret_key="test_secret",
    )
    assert isinstance(state, str)
    decoded = jwt.decode(state, "test_secret", algorithms=["HS256"])
    assert decoded["provider"] == "google"
    assert decoded["redirect_url"] == "http://localhost/callback"


def test_create_oauth_state_with_action_and_user() -> None:
    state = create_oauth_state(
        provider="google",
        redirect_url="http://localhost/callback",
        secret_key="test_secret",
        action="login",
        user_id="user-123",
    )
    decoded = jwt.decode(state, "test_secret", algorithms=["HS256"])
    assert decoded["action"] == "login"
    assert decoded["user_id"] == "user-123"


def test_verify_oauth_state_success() -> None:
    state = create_oauth_state(
        provider="google",
        redirect_url="http://localhost/callback",
        secret_key="test_secret",
    )
    valid, payload, error = verify_oauth_state(state, "google", "test_secret")
    assert valid is True
    assert payload["provider"] == "google"
    assert error == ""


def test_verify_oauth_state_wrong_provider() -> None:
    state = create_oauth_state(
        provider="google",
        redirect_url="http://localhost/callback",
        secret_key="test_secret",
    )
    valid, payload, error = verify_oauth_state(state, "github", "test_secret")
    assert valid is False
    assert error == "Invalid OAuth provider"


def test_verify_oauth_state_expired() -> None:
    payload = {
        "provider": "google",
        "redirect_url": "http://localhost/callback",
        "exp": int(time.time()) - 100,
        "iat": int(time.time()) - 200,
    }
    state = jwt.encode(payload, "test_secret", algorithm="HS256")
    valid, _, error = verify_oauth_state(state, "google", "test_secret")
    assert valid is False
    assert error == "OAuth session expired"


def test_verify_oauth_state_invalid_token() -> None:
    valid, _, error = verify_oauth_state("invalid_token", "google", "test_secret")
    assert valid is False
    assert error == "Invalid OAuth state"


def test_build_oauth_error_redirect() -> None:
    url = build_oauth_error_redirect(
        "http://localhost/callback",
        "invalid_request",
        "Something went wrong",
    )
    assert (
        url
        == "http://localhost/callback?error=invalid_request&message=Something+went+wrong"
    )


def test_build_oauth_error_redirect_with_query_params() -> None:
    url = build_oauth_error_redirect(
        "http://localhost/callback?existing=param",
        "invalid_request",
        "Something went wrong",
    )
    assert (
        url
        == "http://localhost/callback?existing=param&error=invalid_request&message=Something+went+wrong"
    )
