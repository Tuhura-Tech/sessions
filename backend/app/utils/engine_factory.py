from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.serialization import decode_json, encode_json
from sqlalchemy import NullPool, event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from app.lib.settings import Settings


def create_sqlalchemy_engine(settings: Settings) -> "AsyncEngine":
    url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")
    if url.startswith("postgresql+asyncpg"):
        # Build engine kwargs - pool args are invalid with NullPool
        engine_kwargs: dict[str, Any] = {
            "url": url,
            "future": True,
            "json_serializer": encode_json,
            "json_deserializer": decode_json,
            "echo": False,
            "echo_pool": False,
            "pool_recycle": 300,
            "pool_pre_ping": False,
        }
        if False:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update(
                {
                    "max_overflow": 10,
                    "pool_size": 5,
                    "pool_timeout": 30,
                    "pool_use_lifo": True,
                }
            )
        engine = create_async_engine(**engine_kwargs)

    elif url.startswith("sqlite+aiosqlite"):
        engine = create_async_engine(
            url=url,
            future=True,
            json_serializer=encode_json,
            json_deserializer=decode_json,
            echo=False,
            echo_pool=False,
            pool_recycle=300,
            pool_pre_ping=False,
        )

        @event.listens_for(engine.sync_engine, "connect")
        def _sqla_on_connect(  # pragma: no cover # pyright: ignore[reportUnusedFunction]
            dbapi_connection: Any,
            _: Any,
        ) -> Any:
            """Override the default begin statement.  The disables the built in begin execution."""
            dbapi_connection.isolation_level = None

        @event.listens_for(engine.sync_engine, "begin")
        def _sqla_on_begin(  # pragma: no cover # pyright: ignore[reportUnusedFunction]
            dbapi_connection: Any,
        ) -> Any:
            """Emits a custom begin"""
            dbapi_connection.exec_driver_sql("BEGIN")

    else:
        raise ValueError("Unsupported database URL scheme")

    return engine
