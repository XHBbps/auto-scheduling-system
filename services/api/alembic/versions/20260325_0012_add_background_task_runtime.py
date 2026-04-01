"""add background task runtime tables

Revision ID: 20260325_0012
Revises: 20260325_0011
Create Date: 2026-03-25 18:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260325_0012"
down_revision = "20260325_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="manual_api"),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sync_job_log_id", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("worker_id", sa.String(length=120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["sync_job_log_id"], ["sync_job_log.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_background_task_status_available",
        "background_task",
        ["status", "available_at", "id"],
        unique=False,
    )
    op.create_index("idx_background_task_dedupe_key", "background_task", ["dedupe_key"], unique=False)
    op.create_index(
        "idx_background_task_sync_job_log_id", "background_task", ["sync_job_log_id"], unique=False
    )
    op.create_index("idx_background_task_task_type", "background_task", ["task_type"], unique=False)

    op.create_table(
        "sync_scheduler_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_state", sa.String(length=50), nullable=False, server_default="stopped"),
        sa.Column("instance_id", sa.String(length=120), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        INSERT INTO sync_scheduler_state (id, enabled, last_state, updated_by)
        VALUES (1, false, 'stopped', 'migration')
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("sync_scheduler_state")
    op.drop_index("idx_background_task_task_type", table_name="background_task")
    op.drop_index("idx_background_task_sync_job_log_id", table_name="background_task")
    op.drop_index("idx_background_task_dedupe_key", table_name="background_task")
    op.drop_index("idx_background_task_status_available", table_name="background_task")
    op.drop_table("background_task")
