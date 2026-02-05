import asyncio
import os
import sys
from datetime import time
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


async def main() -> None:
    _load_database_url_from_env_file()
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.append(str(backend_root))

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import models as m
    from app.lib.settings import settings

    engine = settings.get_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        existing_count = await session.scalar(
            select(func.count()).select_from(m.Session)
        )
        if existing_count and existing_count > 0:
            print("Seed data already present. Skipping.")
            return

        location = m.Location(
            name="Tūhura Tech Hub",
            address="123 Example Street, Wellington",
            region="Wellington",
            lat=-41.2865,
            lng=174.7762,
            instructions="Enter via main reception.",
            contact_name="Test Contact",
            contact_email="contact@example.com",
            contact_phone="+64-4-000-0000",
            internal_notes="Seeded by scripts/seed.py for E2E tests.",
        )
        session.add(location)
        await session.flush()

        session.add(
            m.Session(
                location_id=location.id,
                year=2026,
                session_type="term",
                name="Beginner Coding Club",
                age_lower=8,
                age_upper=12,
                day_of_week=2,
                start_time=time(15, 30),
                end_time=time(17, 0),
                capacity=20,
                what_to_bring="Laptop and charger",
                prerequisites=None,
                archived=False,
            )
        )

        await session.commit()
        print("Seeded sample location and session data.")


if __name__ == "__main__":
    asyncio.run(main())
