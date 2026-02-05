from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class LocationService(service.SQLAlchemyAsyncRepositoryService[m.Location]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Location]):
        """Location repository."""

        model_type = m.Location

    repository_type = Repo
