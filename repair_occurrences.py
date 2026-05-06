import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


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


def _compute_occurrence_dates(
    block_start,
    block_end,
    day_of_week_int: int,
    exclusions: set,
) -> list:
    # Convert DayOfWeekEnum (0=Sun..6=Sat) to Python weekday (0=Mon..6=Sun)
    day_of_week_python = (day_of_week_int - 1) % 7
    day = block_start
    days_ahead = (day_of_week_python - day.weekday() + 7) % 7
    day = day + timedelta(days=days_ahead)

    dates = []
    while day <= block_end:
        if day not in exclusions:
            dates.append(day)
        day += timedelta(weeks=1)

    return dates


async def _load_exclusions(session, models) -> dict[int, set]:
    results = await session.execute(models.ExclusionDate.__table__.select())
    exclusions_by_year: dict[int, set] = {}
    for row in results.mappings():
        year = row["year"]
        date = row["date"]
        exclusions_by_year.setdefault(year, set()).add(date)
    return exclusions_by_year


async def repair_occurrences(
    *,
    apply_changes: bool,
    force_recreate: bool,
    session_ids: Iterable[str] | None,
) -> None:
    _load_database_url_from_env_file()
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.append(str(backend_root))

    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import models as m
    from app.lib.settings import settings

    engine = settings.get_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as db:
        exclusions_by_year = await _load_exclusions(db, m)

        stmt = select(m.Session).where(m.Session.session_type == "term")
        if session_ids:
            stmt = stmt.where(m.Session.id.in_(list(session_ids)))

        sessions = (await db.execute(stmt)).scalars().all()
        if not sessions:
            print("No term sessions found.")
            return

        local_tz = ZoneInfo("Pacific/Auckland")
        for sess in sessions:
            if sess.day_of_week is None:
                print(f"Skipping session {sess.id} (day_of_week is NULL)")
                continue

            block_links = (
                await db.execute(
                    select(m.BlockLink).where(m.BlockLink.session_id == sess.id)
                )
            ).scalars().all()

            if not block_links:
                print(f"Skipping session {sess.id} (no block links)")
                continue

            for link in block_links:
                block = await db.get(m.Block, link.block_id)
                if not block:
                    print(
                        f"Skipping session {sess.id} block {link.block_id} (missing block)"
                    )
                    continue

                exclusions = exclusions_by_year.get(sess.year, set())
                desired_dates = _compute_occurrence_dates(
                    block.start_date,
                    block.end_date,
                    int(sess.day_of_week),
                    exclusions,
                )

                occurrences = (
                    await db.execute(
                        select(m.Occurrence)
                        .where(
                            m.Occurrence.session_id == sess.id,
                            m.Occurrence.block_id == block.id,
                        )
                        .order_by(m.Occurrence.starts_at)
                    )
                ).scalars().all()

                if len(occurrences) != len(desired_dates):
                    print(
                        "Mismatch for session "
                        f"{sess.id} block {block.id}: "
                        f"{len(occurrences)} existing vs {len(desired_dates)} expected"
                    )

                    if apply_changes and force_recreate:
                        await db.execute(
                            delete(m.Occurrence).where(
                                m.Occurrence.session_id == sess.id,
                                m.Occurrence.block_id == block.id,
                            )
                        )
                        for day in desired_dates:
                            starts_at_local = datetime.combine(
                                day, sess.start_time, tzinfo=local_tz
                            )
                            ends_at_local = datetime.combine(
                                day, sess.end_time, tzinfo=local_tz
                            )
                            db.add(
                                m.Occurrence(
                                    session_id=sess.id,
                                    block_id=block.id,
                                    starts_at=starts_at_local.astimezone(timezone.utc),
                                    ends_at=ends_at_local.astimezone(timezone.utc),
                                )
                            )
                        print(
                            f"Recreated {len(desired_dates)} occurrences for session {sess.id}"
                        )
                    else:
                        print(
                            "Skipping due to mismatch. "
                            "Use --force-recreate with --apply to replace occurrences."
                        )
                    continue

                for occurrence, day in zip(occurrences, desired_dates, strict=False):
                    new_start_local = datetime.combine(
                        day, sess.start_time, tzinfo=local_tz
                    )
                    new_end_local = datetime.combine(day, sess.end_time, tzinfo=local_tz)
                    new_start = new_start_local.astimezone(timezone.utc)
                    new_end = new_end_local.astimezone(timezone.utc)
                    if occurrence.starts_at != new_start or occurrence.ends_at != new_end:
                        print(
                            f"Updating occurrence {occurrence.id}: "
                            f"{occurrence.starts_at} -> {new_start}"
                        )
                        if apply_changes:
                            occurrence.starts_at = new_start
                            occurrence.ends_at = new_end

        if apply_changes:
            await db.commit()
            print("Changes applied.")
        else:
            print("Dry run only. Re-run with --apply to persist changes.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair term session occurrences after day_of_week fix."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to the database (default is dry-run).",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Delete and recreate occurrences if counts mismatch.",
    )
    parser.add_argument(
        "--session-id",
        action="append",
        dest="session_ids",
        help="Limit to a specific session ID (repeatable).",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    await repair_occurrences(
        apply_changes=args.apply,
        force_recreate=args.force_recreate,
        session_ids=args.session_ids,
    )


if __name__ == "__main__":
    asyncio.run(main())
