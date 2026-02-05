from advanced_alchemy.extensions.litestar import repository, service
from app.db import models as m


class AuthMagicLinkService(
    service.SQLAlchemyAsyncRepositoryService[m.CaregiverMagicLink]
):
    """Caregiver service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.CaregiverMagicLink]):
        """Caregiver repository."""

        model_type = m.CaregiverMagicLink

    repository_type = Repo


class AuthSessionService(service.SQLAlchemyAsyncRepositoryService[m.CaregiverSession]):
    """Caregiver service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.CaregiverSession]):
        """Caregiver repository."""

        model_type = m.CaregiverSession

    repository_type = Repo
