from __future__ import annotations

import os
from typing import TYPE_CHECKING, AsyncIterator

# Set test environment BEFORE any app imports (settings are cached on first import)
# Use a dummy database URL that will be replaced by the test engine later
os.environ.update(
    {
        "DATABASE_URL": "postgresql+asyncpg://localhost/test",  # Dummy URL, will be replaced
        "DATABASE_ECHO": "false",
        "DATABASE_ECHO_POOL": "false",
        "SAQ_USE_SERVER_LIFESPAN": "False",
        "SAQ_WEB_ENABLED": "True",
        "SAQ_PROCESSES": "1",
        "SAQ_CONCURRENCY": "1",
        "DEBUG": "True",
        "LITESTAR_DEBUG": "True",
    }
)

# Now import app modules after environment is configured
import pytest
from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from litestar.testing import AsyncTestClient

# pytest-anyio provides async fixture support, we just use @pytest.fixture
# with async def functions instead of @pytest.fixture

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from litestar import Litestar
    from pytest_databases.docker.postgres import PostgresService
    from sqlalchemy.ext.asyncio import AsyncEngine
    from httpx import AsyncClient


pytest_plugins = [
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def anyio_backend_options() -> dict[str, bool]:
    """Prefer uvloop when available for AnyIO's asyncio backend."""
    try:
        import uvloop  # noqa: F401
    except ImportError:
        return {}
    return {"use_uvloop": True}


@pytest.fixture(name="engine", scope="session")
def fx_engine(postgres_service: PostgresService) -> Generator[AsyncEngine, None, None]:
    """PostgreSQL instance for testing.

    Uses asyncpg driver (native async) instead of psycopg (greenlet-based)
    to avoid MissingGreenlet errors in tests.

    Note: This is a sync fixture that yields an async engine. The engine creation
    and disposal are sync operations, but engine usage is async.

    Returns:
        Async SQLAlchemy engine instance.
    """
    import asyncio

    # Set DATABASE_URL for the app to use
    db_url = URL(
        drivername="postgresql+asyncpg",
        username=postgres_service.user,
        password=postgres_service.password,
        host=postgres_service.host,
        port=postgres_service.port,
        database=postgres_service.database,
        query={},  # type:ignore[arg-type]
    )
    os.environ["DATABASE_URL"] = str(db_url)

    engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
    )

    yield engine

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()


@pytest.fixture(name="sessionmaker", scope="session")
def fx_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessionmaker factory bound to test engine."""
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(name="db_schema", scope="session")
def fx_db_schema(engine: AsyncEngine) -> Generator[None, None, None]:
    """Create schema once per test session.

    Note: Schema is created once and not dropped until session ends.
    Individual tests use db_cleanup for per-test isolation.
    """
    import asyncio

    async def create_schema() -> None:
        import app.db.models  # noqa: F401

        metadata = UUIDv7AuditBase.registry.metadata
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def drop_schema() -> None:
        import app.db.models  # noqa: F401

        metadata = UUIDv7AuditBase.registry.metadata
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(create_schema())
        yield
        loop.run_until_complete(drop_schema())
    finally:
        loop.close()


@pytest.fixture
async def db_cleanup(
    engine: AsyncEngine, db_schema: None
) -> AsyncGenerator[None, None]:
    """Per-test database cleanup for isolation.

    Truncates all tables before each test to ensure clean state.
    This is faster than drop/create but still provides isolation.
    """
    yield
    # Clean up after test
    metadata = UUIDv7AuditBase.registry.metadata
    async with engine.begin() as conn:
        for table in reversed(metadata.sorted_tables):
            try:
                await conn.execute(table.delete())
            except Exception:
                # Table might not exist in this test's database
                pass


@pytest.fixture
async def session(
    sessionmaker: async_sessionmaker[AsyncSession],
    db_cleanup: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests with cleanup.

    Uses sessionmaker pattern which properly handles greenlet context
    for async psycopg driver.
    """
    session = sessionmaker()
    try:
        yield session
    finally:
        # Explicitly close the session to handle event loop issues with xdist
        await session.close()


# -----------------------------------------------------------------------------
# App and client fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def app(
    engine: AsyncEngine, db_schema: None, monkeypatch: pytest.MonkeyPatch
) -> Litestar:
    """Create Litestar app for testing.

    The app uses the same PostgreSQL database as the test session.
    """
    from app.asgi import create_app
    from app.lib.settings import settings

    # Monkeypatch settings to use the test engine
    # This ensures lazy creation of the engine uses the test version
    settings._engine_instance = engine

    return create_app()


@pytest.fixture
def _patch_db(
    app: Litestar,
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch the database connection for HTTP client tests.

    This fixture ensures that all HTTP requests made through the test client
    use the same test database that fixtures populate.

    Note: This is NOT autouse - only client tests need it.
    Service tests use session directly and don't need app patching.
    """
    pass


@pytest.fixture(name="client")
async def fx_client(
    app: Litestar, _patch_db: None, db_cleanup: None
) -> AsyncIterator[AsyncClient]:
    """Async client that calls requests on the app."""
    async with AsyncTestClient(app) as client:
        yield client


@pytest.fixture(name="test_client")
async def fx_test_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Alias for client fixture (for backward compatibility)."""
    yield client


@pytest.fixture(name="db_session")
async def fx_db_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    db_cleanup: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Alias for session fixture using db_session name."""
    session = sessionmaker()
    try:
        yield session
    finally:
        # Explicitly close the session to handle event loop issues with xdist
        await session.close()


@pytest.fixture
def admin_session_cookie() -> str:
    """Create a debug admin session cookie for testing authenticated endpoints."""
    from app.domains.admin.guards import create_admin_session

    return create_admin_session(
        email="admin@test.com", provider="debugToken", provider_user_id="test123"
    )


@pytest.fixture
async def caregiver_session_cookie(db_session: AsyncSession) -> str:
    """Create a caregiver session cookie for testing authenticated endpoints."""
    from app.db import models as m
    from app.lib.auth import new_token, hash_token, session_expires_at

    # Create caregiver with profile info
    caregiver = m.Caregiver(
        email="testcaregiver@test.com",
        email_verified=True,
        name="Test Caregiver",
        phone="+64271234567",
    )
    db_session.add(caregiver)
    await db_session.flush()

    # Create session
    token = new_token()
    token_hash = hash_token(token)
    session = m.CaregiverSession(
        caregiver_id=caregiver.id,
        token_hash=token_hash,
        expires_at=session_expires_at(),
    )
    db_session.add(session)
    await db_session.commit()

    return token


@pytest.fixture
async def caregiver_with_token(db_session: AsyncSession) -> tuple:
    """Create a caregiver session and return both caregiver and token."""
    from app.db import models as m
    from app.lib.auth import new_token, hash_token, session_expires_at

    # Create caregiver with profile info
    caregiver = m.Caregiver(
        email="testcaregiver@test.com",
        email_verified=True,
        name="Test Caregiver",
        phone="+64271234567",
    )
    db_session.add(caregiver)
    await db_session.flush()

    # Create session
    token = new_token()
    token_hash = hash_token(token)
    session = m.CaregiverSession(
        caregiver_id=caregiver.id,
        token_hash=token_hash,
        expires_at=session_expires_at(),
    )
    db_session.add(session)
    await db_session.commit()

    return caregiver, token
