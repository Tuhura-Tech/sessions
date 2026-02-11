import asyncio
import os
import sys
from pathlib import Path


def _load_database_url_from_env_file() -> None:
    if os.environ.get("DATABASE_URL"):
        return

    backend_env_path = Path(__file__).resolve().parents[1] / ".env"
    root_env_path = Path(__file__).resolve().parents[2] / ".env"

    for env_path in (backend_env_path, root_env_path):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "DATABASE_URL":
                os.environ["DATABASE_URL"] = value.strip()
                return


async def reset_database() -> None:
    _load_database_url_from_env_file()
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.append(str(backend_root))

    from sqlalchemy import text

    from app.lib.settings import settings

    engine = settings.get_engine()
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        await connection.execute(text("CREATE SCHEMA public;"))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_database())
    print("✅ Database schema reset complete.")
