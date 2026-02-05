from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class BlockLinkService(service.SQLAlchemyAsyncRepositoryService[m.BlockLink]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.BlockLink]):
        """Location repository."""

        model_type = m.BlockLink

    repository_type = Repo
