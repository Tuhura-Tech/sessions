from advanced_alchemy.extensions.litestar import repository, service
from app.db import models as m


class CaregiverService(service.SQLAlchemyAsyncRepositoryService[m.Caregiver]):
    """Caregiver service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Caregiver]):
        """Caregiver repository."""

        model_type = m.Caregiver

    repository_type = Repo
