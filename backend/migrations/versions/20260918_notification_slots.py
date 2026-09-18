"""Morning/evening notification slots, timezone provenance, conversation follow-ups

Revision ID: 20260918_notification_slots
Revises: 20260911_seed_admin_owners
Create Date: 2026-09-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260918_notification_slots"
down_revision = "20260911_seed_admin_owners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("evening_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("evening_hour", sa.Integer(), nullable=False, server_default="21"),
    )
    op.add_column("users", sa.Column("last_evening_notification_date", sa.Date(), nullable=True))
    # Where reminder_timezone came from: default | language | device | manual. A silent
    # device zone from the Mini App must never overwrite a zone the user picked by hand.
    op.add_column(
        "users",
        sa.Column(
            "timezone_source", sa.String(length=16), nullable=False, server_default="default"
        ),
    )
    # Morning/evening messages sent since the user last reacted; drives the auto-decay.
    op.add_column(
        "users",
        sa.Column("unanswered_notifications", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("last_webapp_open_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "conversations",
        sa.Column("followup_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Russian-speaking users who never set a zone sat on UTC, which put the 09:00 message at
    # midday in Moscow and mid-afternoon in Almaty. UTC+4 splits the CIS spread; a device
    # zone from the Mini App replaces it on the next open.
    op.execute(
        "UPDATE users SET reminder_timezone = 'Etc/GMT-4', timezone_source = 'language' "
        "WHERE language = 'ru' AND reminder_timezone = 'UTC'"
    )


def downgrade() -> None:
    op.drop_column("conversations", "followup_sent_at")
    op.drop_column("conversations", "summary")
    op.drop_column("users", "last_webapp_open_at")
    op.drop_column("users", "unanswered_notifications")
    op.drop_column("users", "timezone_source")
    op.drop_column("users", "last_evening_notification_date")
    op.drop_column("users", "evening_hour")
    op.drop_column("users", "evening_enabled")
