from advanced_alchemy.extensions.litestar import repository, service
from app.db import models as m


class StudentService(service.SQLAlchemyAsyncRepositoryService[m.Student]):
    """Signup service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Student]):
        """Signup repository."""

        model_type = m.Student

    repository_type = Repo
