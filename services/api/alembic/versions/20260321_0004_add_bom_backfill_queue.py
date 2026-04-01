"""add bom backfill queue

Revision ID: 20260321_0004
Revises: 20260320_0003
Create Date: 2026-03-21 00:00:04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260321_0004"
down_revision = "20260320_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("bom_backfill_queue"):
        return

    op.create_table(
        "bom_backfill_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_no", sa.String(length=100), nullable=False),
        sa.Column("plant", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("trigger_reason", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_kind", sa.String(length=50), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("first_detected_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("last_job_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("material_no", "plant", name="uk_bom_backfill_queue_material_plant"),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bom_backfill_queue_status_retry "
        "ON bom_backfill_queue (status, next_retry_at, priority, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bom_backfill_queue_source_status "
        "ON bom_backfill_queue (source, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bom_backfill_queue_updated_at "
        "ON bom_backfill_queue (updated_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_bom_backfill_queue_updated_at")
    op.execute("DROP INDEX IF EXISTS idx_bom_backfill_queue_source_status")
    op.execute("DROP INDEX IF EXISTS idx_bom_backfill_queue_status_retry")
    op.drop_table("bom_backfill_queue")
