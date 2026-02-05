from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from litestar.exceptions import HTTPException

from app.domains.admin.controllers.auth import (
    AdminAuthController,
    GOOGLE_AUTH_URL,
    _cookie_domain_from_url,
    _cookie_settings,
)
from app.lib.settings import settings


@dataclass
class DummyRequest:
    url: str = "https://admin.example.com/api/v1/admin/auth/google/callback"
    _query_params: dict[str, str] | None = None

    def url_for(self, _: str) -> str:
        return self.url

    @property
    def query_params(self) -> dict[str, str]:
        return self._query_params or {}


def make_controller() -> AdminAuthController:
    return AdminAuthController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestAdminAuthHelpers:
    def test_cookie_domain_from_url(self) -> None:
        assert _cookie_domain_from_url("http://localhost:3000") is None
        assert _cookie_domain_from_url("http://127.0.0.1:3000") is None
        assert _cookie_domain_from_url("https://admin.example.com") == ".example.com"
        assert _cookie_domain_from_url("https://example.com") is None

    def test_cookie_settings_http_and_https(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "admin_base_url", "http://admin.example.com")
        secure, samesite = _cookie_settings()
        assert secure is False
        assert samesite == "lax"

        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")
        secure, samesite = _cookie_settings()
        assert secure is True
        assert samesite == "none"


@pytest.mark.anyio
class TestAdminAuthController:
    async def test_google_start_requires_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_google_oauth_client_id", "")
        monkeypatch.setattr(settings, "admin_google_oauth_client_secret", "")

        with pytest.raises(HTTPException):
            await AdminAuthController.google_start.fn(controller, DummyRequest())

    async def test_google_start_redirects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_google_oauth_client_id", "client")
        monkeypatch.setattr(settings, "admin_google_oauth_client_secret", "secret")
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")

        response = await AdminAuthController.google_start.fn(controller, DummyRequest())
        assert response.status_code == 302
        assert GOOGLE_AUTH_URL in response.headers.get("Location", "")
        assert "client_id=client" in response.headers.get("Location", "")

    async def test_google_callback_error_redirect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")

        response = await AdminAuthController.google_callback.fn(
            controller, DummyRequest(), error="access_denied"
        )
        assert response.status_code == 302
        assert "oauth_error" in response.headers.get("Location", "")

    async def test_google_callback_missing_params(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")

        response = await AdminAuthController.google_callback.fn(
            controller, DummyRequest()
        )
        assert response.status_code == 302
        assert "oauth_error" in response.headers.get("Location", "")

    async def test_google_callback_invalid_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")

        async def fake_exchange(_: str, __: str) -> dict[str, Any]:
            return {"access_token": "token"}

        async def fake_userinfo(_: str) -> dict[str, Any]:
            return {"email": "admin@example.com", "sub": "123"}

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth.verify_oauth_state",
            lambda **_: (False, {}, "Invalid OAuth state"),
        )
        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._exchange_code_for_token",
            fake_exchange,
        )
        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._fetch_google_userinfo",
            fake_userinfo,
        )

        request = DummyRequest(_query_params={"state": "state"})
        response = await AdminAuthController.google_callback.fn(
            controller, request, code="code"
        )
        assert response.status_code == 302
        assert "Invalid+OAuth+state" in response.headers.get("Location", "")

    async def test_google_callback_missing_access_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")
        monkeypatch.setattr(settings, "auth_secret", "secret")

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth.verify_oauth_state",
            lambda **_: (True, {"redirect_url": "https://admin.example.com"}, ""),
        )

        async def fake_exchange(_: str, __: str) -> dict[str, Any]:
            return {}

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._exchange_code_for_token",
            fake_exchange,
        )

        request = DummyRequest(_query_params={"state": "state"})
        response = await AdminAuthController.google_callback.fn(
            controller, request, code="code"
        )
        assert response.status_code == 302
        assert "Missing+access+token" in response.headers.get("Location", "")

    async def test_google_callback_missing_userinfo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")
        monkeypatch.setattr(settings, "auth_secret", "secret")

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth.verify_oauth_state",
            lambda **_: (True, {"redirect_url": "https://admin.example.com"}, ""),
        )

        async def fake_exchange(_: str, __: str) -> dict[str, Any]:
            return {"access_token": "token"}

        async def fake_userinfo(_: str) -> dict[str, Any]:
            return {}

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._exchange_code_for_token",
            fake_exchange,
        )
        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._fetch_google_userinfo",
            fake_userinfo,
        )

        request = DummyRequest(_query_params={"state": "state"})
        response = await AdminAuthController.google_callback.fn(
            controller, request, code="code"
        )
        assert response.status_code == 302
        assert "Missing+user+info" in response.headers.get("Location", "")

    async def test_google_callback_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        controller = make_controller()
        monkeypatch.setattr(settings, "admin_base_url", "https://admin.example.com")
        monkeypatch.setattr(settings, "auth_secret", "secret")

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth.verify_oauth_state",
            lambda **_: (
                True,
                {"redirect_url": "https://admin.example.com/dashboard"},
                "",
            ),
        )

        async def fake_exchange(_: str, __: str) -> dict[str, Any]:
            return {"access_token": "token"}

        async def fake_userinfo(_: str) -> dict[str, Any]:
            return {"email": "Admin@Example.Com", "sub": "123"}

        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._exchange_code_for_token",
            fake_exchange,
        )
        monkeypatch.setattr(
            "app.domains.admin.controllers.auth._fetch_google_userinfo",
            fake_userinfo,
        )

        request = DummyRequest(_query_params={"state": "state"})
        response = await AdminAuthController.google_callback.fn(
            controller, request, code="code"
        )
        assert response.status_code == 302
        assert response.headers.get("Location") == "https://admin.example.com/dashboard"
        assert any(cookie.key == "admin_session" for cookie in response.cookies)
