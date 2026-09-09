"""seed admin_accounts from OPS_ADMIN_IDS, which stops being a source of access

Revision ID: 20260911_seed_admin_owners
Revises: 20260910_segments_broadcasts
Create Date: 2026-09-11 10:00:00.000000

The ids are read from the environment at upgrade time rather than hardcoded here: they would
otherwise sit in git forever and be applied to every environment. Deploy this while
`OPS_ADMIN_IDS` is still set, check `/admin/access`, and only then drop the variable.

Ids without a `users` row are skipped - access hangs off an existing user, and inserting one
would fake a signup in the product metrics. Use `scripts/grant_admin.py` for those.
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "20260911_seed_admin_owners"
down_revision = "20260910_segments_broadcasts"
branch_labels = None
depends_on = None

NOTE = "migrated from OPS_ADMIN_IDS"


def _env_ids() -> list[int]:
    ids = []
    for value in os.environ.get("OPS_ADMIN_IDS", "").split(","):
        raw = value.strip()
        if not raw:
            continue
        try:
            ids.append(int(raw))
        except ValueError:
            continue
    return ids


def upgrade() -> None:
    ids = _env_ids()
    if not ids:
        return
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO admin_accounts (user_id, role_id, note, granted_by, created_at, updated_at)
            SELECT users.id, 'owner', :note, NULL, now(), now()
            FROM users
            WHERE users.id = ANY(:ids)
            ON CONFLICT (user_id) DO NOTHING
            """
        ),
        {"ids": ids, "note": NOTE},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM admin_accounts WHERE note = :note"), {"note": NOTE}
    )
