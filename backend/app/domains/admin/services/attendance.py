from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class AttendanceService(service.SQLAlchemyAsyncRepositoryService[m.AttendanceRecord]):
    """Attendance service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.AttendanceRecord]):
        """Attendance repository."""

        model_type = m.AttendanceRecord

    repository_type = Repo
