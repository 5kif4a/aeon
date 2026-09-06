"""users.username for ops notifications and the admin panel

Revision ID: 20260909_user_username
Revises: 20260908_bot_settings
Create Date: 2026-09-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260909_user_username"
down_revision = "20260908_bot_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "username")
