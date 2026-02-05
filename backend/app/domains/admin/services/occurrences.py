from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class OccurrenceService(service.SQLAlchemyAsyncRepositoryService[m.Occurrence]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Occurrence]):
        """Location repository."""

        model_type = m.Occurrence

    repository_type = Repo
