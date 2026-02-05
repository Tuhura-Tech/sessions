from advanced_alchemy.extensions.litestar import repository, service
from app.db import models as m


class SessionService(service.SQLAlchemyAsyncRepositoryService[m.Session]):
    """Session service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Session]):
        """Session repository."""

        model_type = m.Session

    repository_type = Repo
