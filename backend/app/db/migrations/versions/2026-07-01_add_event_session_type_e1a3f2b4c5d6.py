"""add_event_session_type

Revision ID: e1a3f2b4c5d6
Revises: c7f9a1e2k3m
Create Date: 2026-07-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e1a3f2b4c5d6"
down_revision = "c7f9a1e2k3m"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update session_type check constraints to include 'event'.
    
    Works for both fresh databases (table may not exist) and existing ones.
    Uses raw SQL with IF EXISTS to be idempotent.
    """
    # Drop old constraints if they exist (safe for all database states)
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_ck_sessions_type CASCADE")
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_type CASCADE")
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_ck_sessions_term_requires_schedule CASCADE")
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_term_requires_schedule CASCADE")

    # Create new constraints (will only affect tables that exist)
    # Check if table exists before creating constraints
    conn = op.get_bind()
    
    # Use information_schema to safely check if table exists
    try:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions')"
            )
        )
        table_exists = result.scalar()
    except Exception:  # noqa: BLE001 - Catch all to handle any database state
        table_exists = False

    if table_exists:
        # Add new constraints
        op.create_check_constraint(
            "ck_sessions_type",
            "sessions",
            "session_type IN ('term','special','event')",
        )

        op.create_check_constraint(
            "ck_sessions_term_requires_schedule",
            "sessions",
            "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special') OR (session_type = 'event')",
        )


def downgrade() -> None:
    """Downgrade: revert to original session_type constraints without 'event'."""
    # Drop the new constraints if they exist
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_type CASCADE")
    op.execute("ALTER TABLE IF EXISTS sessions DROP CONSTRAINT IF EXISTS ck_sessions_term_requires_schedule CASCADE")

    # Check if table exists before creating constraints
    conn = op.get_bind()
    
    try:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions')"
            )
        )
        table_exists = result.scalar()
    except Exception:  # noqa: BLE001
        table_exists = False

    if table_exists:
        # Recreate the old constraints
        op.create_check_constraint(
            "ck_sessions_type",
            "sessions",
            "session_type IN ('term','special')",
        )

        op.create_check_constraint(
            "ck_sessions_term_requires_schedule",
            "sessions",
            "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special')",
        )
