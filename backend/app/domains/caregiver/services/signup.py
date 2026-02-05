from advanced_alchemy.extensions.litestar import repository, service
from app.db import models as m


class SignupService(service.SQLAlchemyAsyncRepositoryService[m.Signup]):
    """Signup service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Signup]):
        """Signup repository."""

        model_type = m.Signup

    repository_type = Repo
