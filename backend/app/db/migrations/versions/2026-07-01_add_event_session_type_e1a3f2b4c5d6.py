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
    # Check if sessions table exists (works for both clean and existing databases)
    conn = op.get_bind()
    inspector = conn.dialect.get_table_names(conn)
    
    if "sessions" not in inspector:
        # Table doesn't exist yet (fresh database), will be created by ORM
        return

    # Drop old constraints with all possible naming conventions
    constraint_names = [
        "ck_sessions_ck_sessions_type",
        "ck_sessions_type",
        "ck_sessions_ck_sessions_term_requires_schedule",
        "ck_sessions_term_requires_schedule",
    ]
    
    for constraint_name in constraint_names:
        try:
            op.drop_constraint(constraint_name, "sessions", type_="check")
        except Exception:
            pass
    
    # Fallback: use raw SQL for any remaining constraints
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
    # Check if sessions table exists
    conn = op.get_bind()
    inspector = conn.dialect.get_table_names(conn)
    
    if "sessions" not in inspector:
        return

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
