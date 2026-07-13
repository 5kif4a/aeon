"""add life weekly notification marker

Revision ID: 20260713_life_weekly
Revises: 4444640b0e86
Create Date: 2026-07-13 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260713_life_weekly"
down_revision = "4444640b0e86"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_life_weekly_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_life_weekly_date")
