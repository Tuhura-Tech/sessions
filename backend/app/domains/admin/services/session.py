from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m
from app.domains.admin.services.block import BlockService
from app.domains.admin.services.block_link import BlockLinkService
from app.domains.admin.services.exclusion import ExclusionService
from app.domains.admin.services.occurrences import OccurrenceService
from app.lib.deps import CompositeServiceMixin


class SessionService(
    CompositeServiceMixin, service.SQLAlchemyAsyncRepositoryService[m.Session]
):
    """Session service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Session]):
        """Session repository."""

        model_type = m.Session

    repository_type = Repo

    @property
    def blocks(self) -> BlockService:
        """Lazy-loaded block service sharing this session.

        Returns:
            The block service instance.
        """
        return self._get_service(BlockService)

    @property
    def occurrences(self) -> OccurrenceService:
        """Lazy-loaded occurrence service sharing this session.

        Returns:
            The occurrence service instance.
        """
        return self._get_service(OccurrenceService)

    @property
    def session_block_service(self) -> BlockLinkService:
        """Lazy-loaded session-block association service.

        Returns:
            The session-block service instance.
        """
        return self._get_service(BlockLinkService)

    @property
    def exclusions(self) -> ExclusionService:
        """Lazy-loaded exclusion service sharing this session.

        Returns:
            The exclusion service instance.
        """
        return self._get_service(ExclusionService)

    @property
    def signups(self):
        """Lazy-loaded signup service sharing this session.

        Returns:
            The signup service instance.
        """
        from app.domains.admin.services.signup import SignupService

        return self._get_service(SignupService)

    @property
    def attendance(self):
        """Lazy-loaded attendance service sharing this session.

        Returns:
            The attendance service instance.
        """
        from app.domains.admin.services.attendance import AttendanceService

        return self._get_service(AttendanceService)
