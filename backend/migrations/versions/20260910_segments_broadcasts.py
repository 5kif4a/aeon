"""audience segments and manual broadcasts with a per-recipient delivery log

Revision ID: 20260910_segments_broadcasts
Revises: 20260910_admin_roles
Create Date: 2026-09-10 12:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260910_segments_broadcasts"
down_revision = "20260910_admin_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="dynamic"),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('dynamic', 'static')", name="ck_user_segments_kind"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_user_segments_name"),
    )

    op.create_table(
        "segment_members",
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["segment_id"], ["user_segments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("segment_id", "user_id"),
    )

    op.create_table(
        "broadcasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False, server_default="marketing"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("markdown", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'sent', 'canceled', 'failed')",
            name="ck_broadcasts_status",
        ),
        sa.CheckConstraint(
            "category IN ('marketing', 'service')", name="ck_broadcasts_category"
        ),
        sa.ForeignKeyConstraint(["segment_id"], ["user_segments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcasts_status", "broadcasts", ["status"])
    op.create_index(
        "ix_broadcasts_status_scheduled_at", "broadcasts", ["status", "scheduled_at"]
    )

    op.create_table(
        "broadcast_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broadcast_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'blocked')",
            name="ck_broadcast_deliveries_status",
        ),
        sa.ForeignKeyConstraint(["broadcast_id"], ["broadcasts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("broadcast_id", "user_id", name="uq_broadcast_deliveries_recipient"),
    )
    op.create_index("ix_broadcast_deliveries_broadcast_id", "broadcast_deliveries", ["broadcast_id"])
    op.create_index("ix_broadcast_deliveries_user_id", "broadcast_deliveries", ["user_id"])
    op.create_index(
        "ix_broadcast_deliveries_broadcast_status",
        "broadcast_deliveries",
        ["broadcast_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_broadcast_deliveries_broadcast_status", table_name="broadcast_deliveries"
    )
    op.drop_index("ix_broadcast_deliveries_user_id", table_name="broadcast_deliveries")
    op.drop_index("ix_broadcast_deliveries_broadcast_id", table_name="broadcast_deliveries")
    op.drop_table("broadcast_deliveries")
    op.drop_index("ix_broadcasts_status_scheduled_at", table_name="broadcasts")
    op.drop_index("ix_broadcasts_status", table_name="broadcasts")
    op.drop_table("broadcasts")
    op.drop_table("segment_members")
    op.drop_table("user_segments")
