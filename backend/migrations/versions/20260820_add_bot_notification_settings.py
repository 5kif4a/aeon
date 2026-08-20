"""add bot notification preferences and daily check-ins

Revision ID: 20260820_bot_ux
Revises: 20260721_billing
Create Date: 2026-08-20 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260820_bot_ux"
down_revision = "20260721_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "daily_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "weekly_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "users", sa.Column("reminder_timezone", sa.String(64), nullable=False, server_default="UTC")
    )
    op.add_column(
        "users", sa.Column("reminder_hour", sa.Integer(), nullable=False, server_default="9")
    )
    op.add_column("users", sa.Column("last_daily_checkin_date", sa.Date(), nullable=True))
    op.add_column(
        "users", sa.Column("daily_checkin_streak", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("users", "daily_checkin_streak")
    op.drop_column("users", "last_daily_checkin_date")
    op.drop_column("users", "reminder_hour")
    op.drop_column("users", "reminder_timezone")
    op.drop_column("users", "weekly_notifications_enabled")
    op.drop_column("users", "daily_notifications_enabled")
