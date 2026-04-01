"""hash admin session tokens at rest

Revision ID: 20260323_0009
Revises: 20260323_0008
Create Date: 2026-03-23 12:00:09
"""
from __future__ import annotations

import hashlib
import re

import sqlalchemy as sa
from alembic import op

revision = "20260323_0009"
down_revision = "20260323_0008"
branch_labels = None
depends_on = None

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "admin_session" not in existing_tables:
        return

    rows = bind.execute(sa.text("SELECT id, session_token FROM admin_session")).fetchall()
    for row in rows:
        session_token = row.session_token
        if not session_token or _SHA256_HEX_RE.fullmatch(session_token):
            continue
        bind.execute(
            sa.text("UPDATE admin_session SET session_token = :session_token WHERE id = :id"),
            {
                "id": row.id,
                "session_token": hashlib.sha256(session_token.encode("utf-8")).hexdigest(),
            },
        )


def downgrade() -> None:
    # 无法安全恢复已哈希的历史会话令牌，降级时保持当前值不变。
    return
