from pathlib import Path
from typing import Final

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
)
from litestar.utils.module_loader import module_to_os_path
from litestar_saq import SAQConfig, QueueConfig
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine

DEFAULT_MODULE_NAME = "app"
BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)
ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = (
        ""  # "postgresql+asyncpg://postgres:postgres@localhost:5432/sessions"
    )

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Application
    debug: bool = True

    cors_origins: str = "http://localhost:4321,http://localhost:4324,http://localhost:3001,http://localhost:3002,http://localhost:8000,http://localhost:4173,https://sessions.tuhuratech.org.nz,https://sessions-admin.tuhuratech.org.nz"
    public_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:4321"
    admin_base_url: str = "http://localhost:3002"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    # Auth (caregiver magic link)
    auth_secret: str = "dev-secret-change-me"
    magic_link_ttl_minutes: int = 15
    caregiver_session_ttl_days: int = 30

    # Admin auth (OAuth + server-issued session)
    admin_session_ttl_hours: int = 24
    # Admin OAuth (Google)
    admin_google_oauth_client_id: str = ""
    admin_google_oauth_client_secret: str = ""

    # Email
    email_from: str = ""
    email_from_name: str = ""
    email_contact: str = ""
    email_dry_run: bool = False  # When True, log emails instead of sending
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    mailgun_api_url: str = ""

    # Portal URLs
    PORTAL_URL: str = "http://localhost:4321"  # Frontend/caregiver portal URL
    SUPPORT_EMAIL: str = "support@example.com"  # Support contact email

    # Newsletter
    newsletter_webhook_url: str = ""
    newsletter_webhook_token: str = ""

    # Rate limiting
    rate_limit_requests_per_minute: int = 60  # General rate limit
    magic_link_rate_limit_per_minute: int = 3  # Strict limit on magic link endpoint
    magic_link_rate_limit_per_hour: int = (
        10  # Max 10 magic link requests per hour per email
    )

    _engine_instance: AsyncEngine | None = None

    @property
    def engine(self) -> AsyncEngine:
        return self.get_engine()

    def get_engine(self) -> AsyncEngine:
        if self._engine_instance is not None:
            return self._engine_instance
        from app.utils.engine_factory import create_sqlalchemy_engine

        self._engine_instance = create_sqlalchemy_engine(self)
        return self._engine_instance


settings = Settings()


_BACKGROUND_TASKS = [
    "app.lib.worker.send_signup_confirmation_task",
    "app.lib.worker.send_waitlist_promoted_task",
    "app.lib.worker.send_signup_cancelled_task",
    "app.lib.worker.send_caregiver_message_task",
    "app.lib.worker.send_session_cancelled_task",
    "app.lib.worker.send_occurrence_cancelled_task",
    "app.lib.worker.process_signup_approval_task",
    "app.lib.worker.bulk_promote_waitlist_task",
    "app.lib.worker.bulk_withdraw_signups_task",
    "app.lib.worker.send_session_reminder_task",
    "app.lib.worker.process_session_reminders_task",
    "app.lib.worker.notify_newsletter_subscription_task",
]


def _get_saq_settings() -> SAQConfig:
    """Lazily create SAQ settings to avoid Redis connection at import time."""
    return SAQConfig(
        web_enabled=True,
        worker_processes=1,
        use_server_lifespan=True,
        queue_configs=[
            QueueConfig(
                name="background-tasks",
                dsn=settings.redis_url,
                tasks=_BACKGROUND_TASKS,
            ),
        ],
    )


def _get_sqlalchemy_settings() -> SQLAlchemyAsyncConfig:
    """Lazily create SQLAlchemy settings when needed."""
    return SQLAlchemyAsyncConfig(
        engine_instance=settings.get_engine(),
        before_send_handler="autocommit",
        session_config=AsyncSessionConfig(expire_on_commit=False),
        alembic_config=AlembicAsyncConfig(
            version_table_name="ddl_version",
            script_config=f"{BASE_DIR}/db/migrations/alembic.ini",
            script_location=f"{BASE_DIR}/db/migrations",
        ),
    )


# Create this lazily in the app factory, not at import time
sqlalchemy_settings: SQLAlchemyAsyncConfig | None = None
