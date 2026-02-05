from advanced_alchemy.extensions.litestar import repository, service

from app.db import models as m


class StudentService(service.SQLAlchemyAsyncRepositoryService[m.Student]):
    """Location service."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Student]):
        """Location repository."""

        model_type = m.Student

    repository_type = Repo

    @staticmethod
    async def get_student_signups(db_obj: m.Student) -> list[m.Signup]:
        """Get all signups for a given student."""
        return db_obj.signups
