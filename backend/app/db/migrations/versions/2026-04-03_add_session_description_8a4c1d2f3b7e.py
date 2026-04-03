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
    op.add_column("sessions", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "description")
