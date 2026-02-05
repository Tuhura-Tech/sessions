from __future__ import annotations

from unittest.mock import Mock

from app.lib.deps import CompositeServiceMixin


class MockRepository:
    def __init__(self, session: Mock) -> None:
        self.session = session


class MockSubService:
    def __init__(self, session: Mock) -> None:
        self.session = session


class CompositeService(CompositeServiceMixin):
    def __init__(self, repository: MockRepository) -> None:
        self.repository = repository


def test_composite_service_mixin_caches() -> None:
    mock_session = Mock()
    repo = MockRepository(mock_session)
    service = CompositeService(repo)

    # First call should instantiate and cache
    sub1 = service._get_service(MockSubService)
    assert isinstance(sub1, MockSubService)
    assert sub1.session is mock_session

    # Second call should return cached instance
    sub2 = service._get_service(MockSubService)
    assert sub1 is sub2
