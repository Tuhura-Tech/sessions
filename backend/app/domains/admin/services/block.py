from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class BlockService(service.SQLAlchemyAsyncRepositoryService[m.Block]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Block]):
        """Location repository."""

        model_type = m.Block

    repository_type = Repo
