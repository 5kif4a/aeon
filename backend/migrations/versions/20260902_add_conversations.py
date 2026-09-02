"""store agent-specific conversation sessions and messages

Revision ID: 20260902_conversations
Revises: 20260820_bot_ux
Create Date: 2026-09-02 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260902_conversations"
down_revision = "20260820_bot_ux"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_conversations_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"], unique=False)
    op.create_index("ix_conversations_status", "conversations", ["status"], unique=False)
    op.create_index(
        "uq_conversations_active_user",
        "conversations",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'agent')", name="ck_conversation_messages_role"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "position", name="uq_conversation_messages_position"
        ),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE VIEW conversation_overview AS
        SELECT
            c.id AS conversation_id,
            c.user_id AS telegram_id,
            u.name AS user_name,
            c.agent_id,
            c.title,
            c.status,
            c.message_count,
            c.created_at,
            c.updated_at,
            c.closed_at
        FROM conversations AS c
        JOIN users AS u ON u.id = c.user_id
        """
    )
    op.execute(
        """
        CREATE VIEW conversation_messages_view AS
        SELECT
            c.id AS conversation_id,
            c.user_id AS telegram_id,
            u.name AS user_name,
            c.agent_id,
            c.title AS conversation_title,
            c.status AS conversation_status,
            m.position,
            m.role,
            m.text,
            m.created_at,
            c.created_at AS conversation_created_at,
            c.closed_at AS conversation_closed_at
        FROM conversation_messages AS m
        JOIN conversations AS c ON c.id = m.conversation_id
        JOIN users AS u ON u.id = c.user_id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS conversation_messages_view")
    op.execute("DROP VIEW IF EXISTS conversation_overview")
    op.drop_index("ix_conversation_messages_conversation_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("uq_conversations_active_user", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_agent_id", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
