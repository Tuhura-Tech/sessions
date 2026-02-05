from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.caregiver.controllers.auth import (
    CAREGIVER_SESSION_COOKIE,
    CaregiverAuthController,
    _safe_return_to,
)
from app.domains.caregiver.schemas.auth import MagicLinkRequest
from app.lib.settings import settings


@dataclass
class DummyRequest:
    cookies: dict[str, str]


class DummyService:
    def __init__(self, list_results=None, get_result=None):
        self._list_results = list_results or []
        self._get_result = get_result
        self.created: list[dict] = []
        self.updated: list[tuple] = []

    async def list(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._list_results)

    async def get(self, *_args, **_kwargs):
        return self._get_result

    async def create(self, data: dict, **kwargs):  # noqa: ANN001
        self.created.append(data)
        return SimpleNamespace(id=uuid4(), **data)

    async def update(self, data: dict, record_id=None, **kwargs):  # noqa: ANN001
        self.updated.append((record_id, data))
        return SimpleNamespace(id=record_id, **data)


def make_controller() -> CaregiverAuthController:
    return CaregiverAuthController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestCaregiverAuthHelpers:
    def test_safe_return_to(self) -> None:
        assert _safe_return_to(None) == "/account"
        assert _safe_return_to("/account/settings") == "/account/settings"
        assert _safe_return_to("https://evil.com") == "/account"
        assert _safe_return_to("//evil.com") == "/account"
        assert _safe_return_to("javascript:alert(1)") == "/account"


@pytest.mark.anyio
class TestCaregiverAuthController:
    async def test_request_magic_link_creates_new(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        monkeypatch.setattr(settings, "debug", False)

        caregiver_service = DummyService(list_results=[])
        magic_link_service = DummyService(list_results=[])

        response = await CaregiverAuthController.request_magic_link.fn(
            controller,
            auth_magic_link_service=magic_link_service,
            caregiver_service=caregiver_service,
            data=MagicLinkRequest(email="user@example.com"),
        )

        assert response.ok is True
        assert response.debug_token is None
        assert len(caregiver_service.created) == 1
        assert len(magic_link_service.created) >= 1

    async def test_request_magic_link_existing_link(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        controller = make_controller()
        monkeypatch.setattr(settings, "debug", False)

        caregiver = SimpleNamespace(id=uuid4(), email="user@example.com")
        caregiver_service = DummyService(list_results=[caregiver])
        magic_link_service = DummyService(list_results=[SimpleNamespace(id=uuid4())])

        response = await CaregiverAuthController.request_magic_link.fn(
            controller,
            auth_magic_link_service=magic_link_service,
            caregiver_service=caregiver_service,
            data=MagicLinkRequest(email="user@example.com"),
        )

        assert response.ok is True
        assert len(magic_link_service.created) >= 1

    async def test_consume_magic_link_invalid(self):
        controller = make_controller()
        magic_link_service = DummyService(list_results=[])
        session_service = DummyService()
        caregiver_service = DummyService(get_result=None)

        response = await CaregiverAuthController.consume_magic_link.fn(
            controller,
            auth_magic_link_service=magic_link_service,
            auth_session_service=session_service,
            caregiver_service=caregiver_service,
            token="invalid",
        )

        assert response.status_code == 400

    async def test_consume_magic_link_success(self, monkeypatch: pytest.MonkeyPatch):
        controller = make_controller()
        monkeypatch.setattr(settings, "debug", False)
        monkeypatch.setattr(
            settings, "frontend_base_url", "https://frontend.example.com"
        )

        caregiver = SimpleNamespace(id=uuid4(), email="user@example.com")
        link = SimpleNamespace(id=uuid4(), caregiver_id=caregiver.id)

        magic_link_service = DummyService(list_results=[link])
        session_service = DummyService()
        caregiver_service = DummyService(get_result=caregiver)

        response = await CaregiverAuthController.consume_magic_link.fn(
            controller,
            auth_magic_link_service=magic_link_service,
            auth_session_service=session_service,
            caregiver_service=caregiver_service,
            token="valid",
            returnTo="/account",
        )

        assert response.status_code == 302
        assert (
            response.headers.get("Location") == "https://frontend.example.com/account"
        )
        assert any(
            cookie.key == CAREGIVER_SESSION_COOKIE for cookie in response.cookies
        )
        assert len(session_service.created) == 1

    async def test_logout_revokes_session(self):
        controller = make_controller()
        session = SimpleNamespace(id=uuid4(), caregiver_id=uuid4(), revoked_at=None)
        session_service = DummyService(list_results=[session])

        response = await CaregiverAuthController.logout.fn(
            controller,
            auth_session_service=session_service,
            request=DummyRequest(cookies={CAREGIVER_SESSION_COOKIE: "token"}),
        )

        assert response.status_code == 200
        assert any(
            cookie.key == CAREGIVER_SESSION_COOKIE for cookie in response.cookies
        )
        assert len(session_service.updated) == 1
