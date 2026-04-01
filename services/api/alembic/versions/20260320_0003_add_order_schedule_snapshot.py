
"""add order schedule snapshot

Revision ID: 20260320_0003
Revises: 20260320_0002
Create Date: 2026-03-20 00:00:03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260320_0003"
down_revision = "20260320_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("order_schedule_snapshot"):
        return

    op.create_table(
        "order_schedule_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_line_id", sa.Integer(), nullable=False),
        sa.Column("contract_no", sa.String(length=100), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("product_series", sa.String(length=100), nullable=True),
        sa.Column("product_model", sa.String(length=100), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("material_no", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("order_no", sa.String(length=100), nullable=True),
        sa.Column("confirmed_delivery_date", sa.DateTime(), nullable=True),
        sa.Column("drawing_released", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("drawing_release_date", sa.DateTime(), nullable=True),
        sa.Column("schedule_status", sa.String(length=50), nullable=False),
        sa.Column("status_reason", sa.String(length=255), nullable=True),
        sa.Column("trigger_date", sa.DateTime(), nullable=True),
        sa.Column("machine_cycle_days", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_default_cycle", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("machine_schedule_id", sa.Integer(), nullable=True),
        sa.Column("planned_start_date", sa.DateTime(), nullable=True),
        sa.Column("planned_end_date", sa.DateTime(), nullable=True),
        sa.Column("machine_assembly_days", sa.Numeric(18, 4), nullable=True),
        sa.Column("warning_level", sa.String(length=50), nullable=True),
        sa.Column("default_flags", JSONB, nullable=True),
        sa.Column("issue_flags", JSONB, nullable=True),
        sa.Column("last_refresh_source", sa.String(length=50), nullable=True),
        sa.Column("refresh_reason", sa.String(length=255), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_line_id", name="uk_order_schedule_snapshot_order_line_id"),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_status ON order_schedule_snapshot (schedule_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_trigger_date ON order_schedule_snapshot (trigger_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_delivery_date ON order_schedule_snapshot (confirmed_delivery_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_product_model ON order_schedule_snapshot (product_model)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_material_no ON order_schedule_snapshot (material_no)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_schedule_snapshot_machine_schedule_id ON order_schedule_snapshot (machine_schedule_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_machine_schedule_id")
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_material_no")
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_product_model")
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_delivery_date")
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_trigger_date")
    op.execute("DROP INDEX IF EXISTS idx_order_schedule_snapshot_status")
    op.drop_table("order_schedule_snapshot")
