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
    # Update session_type check constraint to include 'event'
    op.drop_constraint("ck_sessions_type", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_type",
        "sessions",
        "session_type IN ('term','special','event')",
    )

    # Update schedule constraint to allow event sessions without day_of_week
    op.drop_constraint("ck_sessions_term_requires_schedule", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_term_requires_schedule",
        "sessions",
        "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special') OR (session_type = 'event')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sessions_term_requires_schedule", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_term_requires_schedule",
        "sessions",
        "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special')",
    )

    op.drop_constraint("ck_sessions_type", "sessions", type_="check")
    op.create_check_constraint(
        "ck_sessions_type",
        "sessions",
        "session_type IN ('term','special')",
    )
