"""admin roles and per-user admin grants (access matrix in the database)

Revision ID: 20260910_admin_roles
Revises: 20260909_user_username
Create Date: 2026-09-10 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260910_admin_roles"
down_revision = "20260909_user_username"
branch_labels = None
depends_on = None

# Seeded once; the panel may re-cut `support` and `marketing`, `owner` stays locked.
SYSTEM_ROLES = (
    ("owner", "Owner", "Full access, including who else is an admin", ["*"]),
    (
        "support",
        "Support",
        "Answers users: reads dialogues, grants Pro, refunds payments",
        [
            "stats.view",
            "users.view",
            "users.grant_pro",
            "conversations.view",
            "payments.view",
            "payments.refund",
        ],
    ),
    (
        "marketing",
        "Marketing",
        "Builds segments and sends broadcasts; no dialogues, no refunds",
        [
            "stats.view",
            "users.view",
            "segments.view",
            "segments.edit",
            "broadcasts.view",
            "broadcasts.edit",
            "broadcasts.send",
        ],
    ),
)


def upgrade() -> None:
    roles = op.create_table(
        "admin_roles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": role_id,
                "title": title,
                "description": description,
                "permissions": permissions,
                "is_system": True,
            }
            for role_id, title, description, permissions in SYSTEM_ROLES
        ],
    )

    op.create_table(
        "admin_accounts",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("granted_by", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["admin_roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_admin_accounts_role_id", "admin_accounts", ["role_id"])

    op.add_column(
        "users",
        sa.Column(
            "marketing_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "marketing_enabled")
    op.drop_index("ix_admin_accounts_role_id", table_name="admin_accounts")
    op.drop_table("admin_accounts")
    op.drop_table("admin_roles")
