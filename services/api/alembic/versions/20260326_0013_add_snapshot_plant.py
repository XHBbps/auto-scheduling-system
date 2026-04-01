"""add plant to order schedule snapshot

Revision ID: 20260326_0013
Revises: 20260325_0012
Create Date: 2026-03-26 00:00:13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260326_0013"
down_revision = "20260325_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("order_schedule_snapshot")}
    if "plant" not in existing_columns:
        op.add_column("order_schedule_snapshot", sa.Column("plant", sa.String(length=50), nullable=True))

    op.execute(
        """
        UPDATE order_schedule_snapshot AS snapshot
        SET plant = src.delivery_plant
        FROM sales_plan_order_line_src AS src
        WHERE snapshot.order_line_id = src.id
          AND snapshot.plant IS NULL
        """
    )
    op.execute(
        """
        UPDATE order_schedule_snapshot AS snapshot
        SET plant = COALESCE(msr.delivery_plant, '1000')
        FROM machine_schedule_result AS msr
        WHERE snapshot.order_line_id = msr.order_line_id
          AND snapshot.plant IS NULL
        """
    )
    op.execute("UPDATE order_schedule_snapshot SET plant = '1000' WHERE plant IS NULL")

    existing_indexes = {index["name"] for index in inspector.get_indexes("order_schedule_snapshot")}
    if "idx_order_schedule_snapshot_plant" not in existing_indexes:
        op.create_index("idx_order_schedule_snapshot_plant", "order_schedule_snapshot", ["plant"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("order_schedule_snapshot")}
    if "idx_order_schedule_snapshot_plant" in existing_indexes:
        op.drop_index("idx_order_schedule_snapshot_plant", table_name="order_schedule_snapshot")

    existing_columns = {column["name"] for column in inspector.get_columns("order_schedule_snapshot")}
    if "plant" in existing_columns:
        op.drop_column("order_schedule_snapshot", "plant")
