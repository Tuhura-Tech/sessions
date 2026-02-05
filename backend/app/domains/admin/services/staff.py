from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class StaffService(service.SQLAlchemyAsyncRepositoryService[m.Staff]):
    """Staff service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Staff]):
        """Staff repository."""

        model_type = m.Staff

    repository_type = Repo


class SessionStaffService(service.SQLAlchemyAsyncRepositoryService[m.SessionStaff]):
    """Session staff assignment service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.SessionStaff]):
        """Session staff repository."""

        model_type = m.SessionStaff

    repository_type = Repo
