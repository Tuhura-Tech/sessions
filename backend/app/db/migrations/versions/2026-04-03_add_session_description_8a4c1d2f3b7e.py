"""add_description_to_sessions

Revision ID: 8a4c1d2f3b7e
Revises: 6bdcb81c216a
Create Date: 2026-04-03 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8a4c1d2f3b7e"
down_revision = "6bdcb81c216a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description column if it doesn't already exist (for prod databases)
    op.execute(
        """
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS description TEXT NULL
        """
    )


def downgrade() -> None:
    # Drop column if it exists
    op.execute(
        """
        ALTER TABLE sessions DROP COLUMN IF EXISTS description
        """
    )
