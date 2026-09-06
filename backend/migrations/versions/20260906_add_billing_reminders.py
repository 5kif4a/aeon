"""track sent Stars billing reminders (trial ending, trial ended, pro expired)

Revision ID: 20260906_billing_reminders
Revises: 20260902_conversations
Create Date: 2026-09-06 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_billing_reminders"
down_revision = "20260902_conversations"
branch_labels = None
depends_on = None

COLUMNS = ("trial_ending_reminded_at", "trial_ended_reminded_at", "pro_expired_reminded_at")


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column("users", sa.Column(column, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column("users", column)
