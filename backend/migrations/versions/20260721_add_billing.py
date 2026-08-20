"""add freemium subscriptions and usage accounting

Revision ID: 20260721_billing
Revises: 20260713_daily_notice
Create Date: 2026-07-21 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260721_billing"
down_revision = "20260713_daily_notice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users", sa.Column("trial_rag_used", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "users", sa.Column("trial_council_used", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("users", sa.Column("pro_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("pro_subscription_charge_id", sa.String(256), nullable=True))
    op.add_column(
        "users", sa.Column("pro_auto_renew", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.execute("UPDATE users SET plan = 'Free'")
    op.alter_column("users", "plan", server_default="Free")

    op.create_table(
        "daily_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("prompt_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rag_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("council_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),
    )
    op.create_index("ix_daily_usages_user_id", "daily_usages", ["user_id"])
    op.create_index("ix_daily_usages_usage_date", "daily_usages", ["usage_date"])

    op.create_table(
        "billing_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("invoice_payload", sa.String(256), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(256), nullable=False),
        sa.Column("provider_payment_charge_id", sa.String(256), nullable=False, server_default=""),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(32), nullable=False, server_default="paid"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_payments_user_id", "billing_payments", ["user_id"])
    op.create_index(
        "ix_billing_payments_telegram_payment_charge_id",
        "billing_payments",
        ["telegram_payment_charge_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_billing_payments_telegram_payment_charge_id", table_name="billing_payments")
    op.drop_index("ix_billing_payments_user_id", table_name="billing_payments")
    op.drop_table("billing_payments")
    op.drop_index("ix_daily_usages_usage_date", table_name="daily_usages")
    op.drop_index("ix_daily_usages_user_id", table_name="daily_usages")
    op.drop_table("daily_usages")
    op.drop_column("users", "pro_auto_renew")
    op.drop_column("users", "pro_subscription_charge_id")
    op.drop_column("users", "pro_expires_at")
    op.drop_column("users", "trial_council_used")
    op.drop_column("users", "trial_rag_used")
    op.drop_column("users", "trial_expires_at")
    op.drop_column("users", "trial_started_at")
    op.alter_column("users", "plan", server_default=None)
