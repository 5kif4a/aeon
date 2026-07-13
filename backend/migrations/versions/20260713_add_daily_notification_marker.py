"""add daily notification marker

Revision ID: 20260713_daily_notice
Revises: 20260713_life_weekly
Create Date: 2026-07-13 18:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260713_daily_notice"
down_revision = "20260713_life_weekly"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_daily_notification_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_daily_notification_date")
