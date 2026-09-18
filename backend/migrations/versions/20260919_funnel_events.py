"""Funnel events: acquisition source, first answer delivered, blocked bot

Revision ID: 20260919_funnel_events
Revises: 20260919_onboarding_pending
Create Date: 2026-09-19 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_funnel_events"
down_revision = "20260919_onboarding_pending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `/start <source>` from ad links and seeds; empty for organic. First touch only.
    op.add_column(
        "users",
        sa.Column("acquired_from", sa.String(64), nullable=False, server_default=""),
    )
    # When the first advisor answer reached the user. The health metric the second iteration
    # lacked: a signup without this within a day means the path /start -> answer is broken.
    op.add_column("users", sa.Column("first_answer_at", sa.DateTime(timezone=True), nullable=True))
    # Telegram answered Forbidden to a notification: the user blocked the bot. Cleared when
    # they write again. Blocked users are skipped by every scheduled send.
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    # Existing users who already got answers must not look like "never answered".
    op.execute(
        """
        UPDATE users AS u
        SET first_answer_at = firsts.first_at
        FROM (
            SELECT c.user_id, MIN(m.created_at) AS first_at
            FROM conversation_messages AS m
            JOIN conversations AS c ON c.id = m.conversation_id
            WHERE m.role = 'agent'
            GROUP BY c.user_id
        ) AS firsts
        WHERE firsts.user_id = u.id
        """
    )


def downgrade() -> None:
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "first_answer_at")
    op.drop_column("users", "acquired_from")
