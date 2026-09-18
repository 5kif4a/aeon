"""Admin user reset: flag that makes the next /start behave like the first one

Revision ID: 20260919_onboarding_pending
Revises: 20260918_notification_slots
Create Date: 2026-09-19 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_onboarding_pending"
down_revision = "20260918_notification_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Set by the admin "reset user" action; /start clears it after showing the welcome again.
    # The user row itself stays, so payments, events and signup metrics are untouched.
    op.add_column(
        "users",
        sa.Column("onboarding_pending", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_pending")
