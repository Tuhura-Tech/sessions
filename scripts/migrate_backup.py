#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import date

import psycopg


@dataclass
class DbConfig:
    dsn: str
    legacy_schema: str


def normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if dsn.startswith("postgresql+psycopg://"):
        return dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


def get_config(args: argparse.Namespace) -> DbConfig:
    dsn = args.database_url or os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL must be provided via --database-url or env var")
    return DbConfig(dsn=normalize_dsn(dsn), legacy_schema=args.legacy_schema)


def run_psql_restore(backup_path: str, dsn: str) -> None:
    cmd = ["psql", dsn, "-f", backup_path]
    print(f"Restoring backup with: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def list_public_tables(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        return [row[0] for row in cur.fetchall()]


def list_public_views(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        return [row[0] for row in cur.fetchall()]


def drop_views(conn: psycopg.Connection) -> None:
    views = list_public_views(conn)
    if not views:
        return
    with conn.cursor() as cur:
        for view in views:
            cur.execute(f'DROP VIEW IF EXISTS public."{view}" CASCADE')


def move_tables_to_legacy(conn: psycopg.Connection, legacy_schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {legacy_schema}")
    drop_views(conn)
    tables = list_public_tables(conn)
    if not tables:
        return
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f'ALTER TABLE public."{table}" SET SCHEMA {legacy_schema}')


def run_alembic_upgrade() -> None:
    env = os.environ.copy()
    env.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
    subprocess.run(
        ["uv", "run", "litestar", "database", "upgrade", "--no-prompt"],
        check=True,
        env=env,
    )


def insert_basic_tables(conn: psycopg.Connection, legacy_schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO locations
                (id, name, address, region, lat, lng, instructions, contact_name, contact_email,
                 contact_phone, internal_notes, created_at, updated_at)
            SELECT id, name, address, region, lat, lng, instructions, contact_name, contact_email,
                   contact_phone, internal_notes, created_at, updated_at
            FROM {legacy_schema}.session_locations
            """
        )

        cur.execute(
            f"""
            INSERT INTO caregivers
                (id, name, email, phone, email_verified, last_login_at, referral_source, created_at, updated_at)
            SELECT id, name, email, phone, email_verified, last_login_at, referral_source, created_at, updated_at
            FROM {legacy_schema}.caregivers
            """
        )

        cur.execute(
            f"""
            INSERT INTO caregiver_magic_links
                (id, caregiver_id, token_hash, expires_at, used_at, created_at, updated_at)
            SELECT id, caregiver_id, token_hash, expires_at, used_at, created_at, updated_at
            FROM {legacy_schema}.caregiver_magic_links
            """
        )

        cur.execute(
            f"""
            INSERT INTO caregiver_sessions
                (id, caregiver_id, token_hash, expires_at, revoked_at, user_agent, ip_address, created_at, updated_at)
            SELECT id, caregiver_id, token_hash, expires_at, revoked_at, user_agent, ip_address, created_at, updated_at
            FROM {legacy_schema}.caregiver_sessions
            """
        )

        cur.execute(
            f"""
            INSERT INTO staff
                (id, name, email, sso_id, last_login_at, active, deactivated_at, created_at, updated_at)
            SELECT id, name, email, sso_id, last_login_at, active, deactivated_at, created_at, updated_at
            FROM {legacy_schema}.staff
            """
        )

        cur.execute(
            f"""
            INSERT INTO exclusion_dates
                (id, year, date, reason, created_at, updated_at)
            SELECT id, year, date, reason, created_at, updated_at
            FROM {legacy_schema}.exclusion_dates
            """
        )

        cur.execute(
            f"""
            INSERT INTO sessions
                (id, location_id, year, session_type, name, age_lower, age_upper, day_of_week,
                 start_time, end_time, capacity, what_to_bring, prerequisites, photo_album_url,
                 internal_notes, archived, created_at, updated_at)
            SELECT id,
                   session_location_id,
                   year,
                   session_type,
                   name,
                   age_lower,
                   age_upper,
                   day_of_week,
                   start_time,
                   end_time,
                   capacity,
                   what_to_bring,
                   prerequisites,
                   photo_album_url,
                   CASE
                       WHEN waitlist IS TRUE AND internal_notes IS NULL THEN 'Legacy: waitlist enabled'
                       WHEN waitlist IS TRUE THEN internal_notes || E'\nLegacy: waitlist enabled'
                       ELSE internal_notes
                   END AS internal_notes,
                   archived,
                   created_at,
                   updated_at
            FROM {legacy_schema}.sessions
            """
        )

        cur.execute(
            f"""
            INSERT INTO students
                (id, caregiver_id, name, date_of_birth, media_consent, medical_info, other_info,
                 region, ethnicity, school_name, gender, archived, created_at, updated_at)
            SELECT id, caregiver_id, name, date_of_birth, media_consent, medical_info, other_info,
                   region, ethnicity, school_name, gender, FALSE, created_at, updated_at
            FROM {legacy_schema}.children
            """
        )

        cur.execute(
            f"""
            INSERT INTO session_staff
                (id, session_id, staff_id, assigned_at, created_at, updated_at)
            SELECT id, session_id, staff_id, assigned_at, assigned_at, assigned_at
            FROM {legacy_schema}.session_staff
            """
        )


def insert_blocks(conn: psycopg.Connection, legacy_schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO blocks
                (id, year, name, block_type, start_date, end_date, created_at, updated_at)
            SELECT id, year, name, block_type, start_date, end_date, created_at, updated_at
            FROM {legacy_schema}.session_blocks
            """
        )
        cur.execute(
            f"""
            INSERT INTO block_links
                (id, session_id, block_id, created_at, updated_at)
            SELECT id, session_id, block_id, created_at, updated_at
            FROM {legacy_schema}.session_block_links
            """
        )


def ensure_fallback_blocks(
    conn: psycopg.Connection, legacy_schema: str
) -> dict[int, uuid.UUID]:
    """Create fallback blocks for sessions without block links.

    Returns mapping of year -> fallback block id.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT s.id, s.year
            FROM {legacy_schema}.sessions s
            LEFT JOIN {legacy_schema}.session_block_links sbl ON sbl.session_id = s.id
            WHERE sbl.id IS NULL
            ORDER BY s.year
            """
        )
        sessions = cur.fetchall()

    fallback_map: dict[int, uuid.UUID] = {}
    if not sessions:
        return fallback_map

    with conn.cursor() as cur:
        for session_id, year in sessions:
            if year not in fallback_map:
                cur.execute(
                    """
                    SELECT id FROM blocks WHERE year = %s AND name = %s
                    """,
                    (year, f"Legacy Imported {year}"),
                )
                row = cur.fetchone()
                if row:
                    fallback_id = row[0]
                else:
                    cur.execute(
                        f"""
                        SELECT
                            COALESCE(MIN(starts_at)::date, %s::date) AS start_date,
                            COALESCE(MAX(ends_at)::date, %s::date) AS end_date
                        FROM {legacy_schema}.session_occurrences so
                        JOIN {legacy_schema}.sessions s ON s.id = so.session_id
                        WHERE s.year = %s
                        """,
                        (date(year, 1, 1), date(year, 12, 31), year),
                    )
                    start_date, end_date = cur.fetchone()
                    fallback_id = uuid.uuid4()
                    cur.execute(
                        """
                        INSERT INTO blocks
                            (id, year, name, block_type, start_date, end_date, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                        """,
                        (
                            fallback_id,
                            year,
                            f"Legacy Imported {year}",
                            "special",
                            start_date,
                            end_date,
                        ),
                    )
                fallback_map[year] = fallback_id

            cur.execute(
                """
                INSERT INTO block_links
                    (id, session_id, block_id, created_at, updated_at)
                VALUES (%s, %s, %s, now(), now())
                """,
                (uuid.uuid4(), session_id, fallback_map[year]),
            )

    return fallback_map


def insert_occurrences_signups_attendance(
    conn: psycopg.Connection, legacy_schema: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO occurrences
                (id, session_id, starts_at, ends_at, cancelled, cancellation_reason, block_id,
                 created_at, updated_at)
            SELECT so.id,
                   so.session_id,
                   so.starts_at,
                   so.ends_at,
                   so.cancelled,
                   so.cancellation_reason,
                   COALESCE(so.block_id, sbl.block_id) AS block_id,
                   so.starts_at,
                   so.starts_at
            FROM {legacy_schema}.session_occurrences so
            LEFT JOIN LATERAL (
                SELECT block_id
                FROM block_links bl
                WHERE bl.session_id = so.session_id
                ORDER BY bl.created_at NULLS LAST
                LIMIT 1
            ) sbl ON TRUE
            """
        )

        cur.execute(
            f"""
            INSERT INTO signups
                (id, session_id, student_id, status, withdrawn_at, pickup_dropoff, needs_devices,
                 created_at, updated_at)
            SELECT s.id,
                   s.session_id,
                   s.child_id,
                   s.status,
                   s.withdrawn_at,
                   s.pickup_dropoff,
                   COALESCE(c.needs_devices, FALSE),
                   s.created_at,
                   s.updated_at
            FROM {legacy_schema}.signups s
            JOIN {legacy_schema}.children c ON c.id = s.child_id
            """
        )

        cur.execute(
            f"""
            INSERT INTO attendance_records
                (id, occurrence_id, student_id, status, reason, created_at, updated_at)
            SELECT id,
                   occurrence_id,
                   child_id,
                   status,
                   reason,
                   now(),
                   now()
            FROM {legacy_schema}.attendance_records
            """
        )


def verify_counts(conn: psycopg.Connection, legacy_schema: str) -> None:
    checks = [
        ("caregivers", "caregivers"),
        ("students", "children"),
        ("locations", "session_locations"),
        ("sessions", "sessions"),
        ("blocks", "session_blocks"),
        ("block_links", "session_block_links"),
        ("occurrences", "session_occurrences"),
        ("signups", "signups"),
        ("attendance_records", "attendance_records"),
        ("staff", "staff"),
        ("session_staff", "session_staff"),
        ("exclusion_dates", "exclusion_dates"),
    ]
    with conn.cursor() as cur:
        print("\nRow count comparison:")
        for new_table, legacy_table in checks:
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            new_count = cur.fetchone()[0]
            cur.execute(f'SELECT COUNT(*) FROM {legacy_schema}."{legacy_table}"')
            legacy_count = cur.fetchone()[0]
            status = "OK" if new_count >= legacy_count else "MISMATCH"
            print(
                f"- {new_table}: {new_count} (legacy {legacy_table}: {legacy_count}) [{status}]"
            )

        print("\nReferential integrity checks:")
        cur.execute(
            """
            SELECT COUNT(*)
            FROM signups s
            LEFT JOIN sessions se ON se.id = s.session_id
            WHERE se.id IS NULL
            """
        )
        print(f"- signups missing sessions: {cur.fetchone()[0]}")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM signups s
            LEFT JOIN students st ON st.id = s.student_id
            WHERE st.id IS NULL
            """
        )
        print(f"- signups missing students: {cur.fetchone()[0]}")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM occurrences o
            LEFT JOIN sessions se ON se.id = o.session_id
            WHERE se.id IS NULL
            """
        )
        print(f"- occurrences missing sessions: {cur.fetchone()[0]}")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM attendance_records ar
            LEFT JOIN occurrences o ON o.id = ar.occurrence_id
            WHERE o.id IS NULL
            """
        )
        print(f"- attendance_records missing occurrences: {cur.fetchone()[0]}")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM attendance_records ar
            LEFT JOIN students st ON st.id = ar.student_id
            WHERE st.id IS NULL
            """
        )
        print(f"- attendance_records missing students: {cur.fetchone()[0]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy backup to new schema")
    parser.add_argument("--backup", help="Path to backup.sql")
    parser.add_argument("--database-url", help="Database URL")
    parser.add_argument(
        "--legacy-schema", default="legacy", help="Schema for legacy tables"
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore backup.sql using psql before migration",
    )
    parser.add_argument(
        "--skip-upgrade",
        action="store_true",
        help="Skip alembic upgrade (assumes schema already created)",
    )
    args = parser.parse_args()

    cfg = get_config(args)

    if args.restore:
        if not args.backup:
            raise SystemExit("--backup is required when --restore is set")
        run_psql_restore(args.backup, cfg.dsn)

    with psycopg.connect(cfg.dsn) as conn:
        conn.execute("SET session_replication_role = 'origin'")
        conn.execute("SET TIME ZONE 'UTC'")
        move_tables_to_legacy(conn, cfg.legacy_schema)
        conn.commit()

    if not args.skip_upgrade:
        run_alembic_upgrade()

    with psycopg.connect(cfg.dsn) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        insert_basic_tables(conn, cfg.legacy_schema)
        insert_blocks(conn, cfg.legacy_schema)
        ensure_fallback_blocks(conn, cfg.legacy_schema)
        insert_occurrences_signups_attendance(conn, cfg.legacy_schema)
        conn.commit()
        verify_counts(conn, cfg.legacy_schema)

    print("\nMigration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
