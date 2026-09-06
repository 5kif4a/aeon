"""embedded RAG corpus chunks stored in Postgres (no pgvector)

Revision ID: 20260908_rag_chunks
Revises: 20260907_product_events
Create Date: 2026-09-08 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_rag_chunks"
down_revision = "20260907_product_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default=""),
        sa.Column("chapter", sa.Text(), nullable=False, server_default=""),
        sa.Column("page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        # L2-normalized vector packed as little-endian float32 (RAG_EMBEDDING_DIM * 4 bytes).
        sa.Column("embedding", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_id", "language", "chunk_id", name="uq_rag_chunks_agent_lang_chunk"
        ),
    )
    op.create_index("ix_rag_chunks_agent_language", "rag_chunks", ["agent_id", "language"])


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_agent_language", table_name="rag_chunks")
    op.drop_table("rag_chunks")
