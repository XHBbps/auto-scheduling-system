"""add dead_at field to background_task

Revision ID: 20260406_0019
Revises: 20260406_0018
Create Date: 2026-04-06 00:19:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0019"
down_revision = "20260406_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("background_task", sa.Column("dead_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("background_task", "dead_at")
