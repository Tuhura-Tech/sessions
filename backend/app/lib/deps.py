"""Application dependency providers generators.

This module contains functions to create dependency providers for services and filters.

You should not have modify this module very often and should only be invoked under normal usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast


if TYPE_CHECKING:
    from saq import Queue

__all__ = ("get_task_queue",)

S = TypeVar("S")


async def get_task_queue() -> Queue:
    """Get the background task queue.

    Returns:
        Queue: The connected background task queue.
    """
    from app.server import plugins

    task_queues = plugins.get_saq_plugin().get_queue("background-tasks")
    await task_queues.connect()

    return task_queues


class CompositeServiceMixin:
    """Mixin for services that orchestrate multiple repositories.

    Provides lazy instantiation of dependent services that share
    the parent service's database session.

    Example:
        ```python
        from app.lib.deps import CompositeServiceMixin

        class UserService(CompositeServiceMixin, SQLAlchemyAsyncRepositoryService[m.User]):
            @property
            def oauth_accounts(self) -> UserOAuthAccountService:
                return self._get_service(UserOAuthAccountService)

            async def authenticate_oauth_user(self, ...) -> m.User:
                await self.oauth_accounts.create_or_update_oauth_account(...)
        ```
    """

    _service_cache: dict[type, Any]

    def _get_service(self, service_cls: type[S]) -> S:
        """Get or create a dependent service instance.

        Args:
            service_cls: The service class to instantiate.

        Returns:
            Cached service instance sharing this service's session.
        """
        if not hasattr(self, "_service_cache"):
            self._service_cache = {}

        if service_cls not in self._service_cache:
            repository = cast("Any", self).repository
            self._service_cache[service_cls] = service_cls(session=repository.session)

        return cast("S", self._service_cache[service_cls])
