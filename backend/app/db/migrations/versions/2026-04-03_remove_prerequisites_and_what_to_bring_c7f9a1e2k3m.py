"""remove_prerequisites_and_what_to_bring

Revision ID: c7f9a1e2k3m
Revises: 8a4c1d2f3b7e
Create Date: 2026-04-03 23:11:27.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f9a1e2k3m"
down_revision = "8a4c1d2f3b7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("sessions", "what_to_bring")
    op.drop_column("sessions", "prerequisites")


def downgrade() -> None:
    op.add_column("sessions", sa.Column("what_to_bring", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("prerequisites", sa.Text(), nullable=True))
