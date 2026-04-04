"""add_event_session_type

Revision ID: e1a3f2b4c5d6
Revises: c7f9a1e2k3m
Create Date: 2026-07-01 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1a3f2b4c5d6"
down_revision = "c7f9a1e2k3m"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing check constraints (handle both naming conventions for clean installs and prod)
    # Try the ORM-generated name first, then fallback to raw SQL for any variant
    try:
        op.drop_constraint("ck_sessions_ck_sessions_type", "sessions", type_="check")
    except Exception:
        pass
    try:
        op.drop_constraint("ck_sessions_type", "sessions", type_="check")
    except Exception:
        pass

    try:
        op.drop_constraint("ck_sessions_ck_sessions_term_requires_schedule", "sessions", type_="check")
    except Exception:
        pass
    try:
        op.drop_constraint("ck_sessions_term_requires_schedule", "sessions", type_="check")
    except Exception:
        pass

    # Use raw SQL as fallback for edge cases
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_ck_sessions_type")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_type")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_ck_sessions_term_requires_schedule")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_term_requires_schedule")

    # Create new constraints with the event type included
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
    # Drop the new constraints
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_type")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS ck_sessions_term_requires_schedule")

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
