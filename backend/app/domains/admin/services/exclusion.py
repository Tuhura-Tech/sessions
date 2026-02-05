from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class ExclusionService(service.SQLAlchemyAsyncRepositoryService[m.ExclusionDate]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.ExclusionDate]):
        """Location repository."""

        model_type = m.ExclusionDate

    repository_type = Repo
