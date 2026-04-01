"""add snapshot query indexes

Revision ID: 20260323_0006
Revises: 20260322_0005
Create Date: 2026-03-23 00:00:06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260323_0006"
down_revision = "20260322_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("order_schedule_snapshot")}

    for index_name, column_name in [
        ("idx_order_schedule_snapshot_contract_no", "contract_no"),
        ("idx_order_schedule_snapshot_order_no", "order_no"),
        ("idx_order_schedule_snapshot_warning_level", "warning_level"),
    ]:
        if index_name not in existing_indexes:
            op.create_index(index_name, "order_schedule_snapshot", [column_name], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("order_schedule_snapshot")}
    for index_name in [
        "idx_order_schedule_snapshot_warning_level",
        "idx_order_schedule_snapshot_order_no",
        "idx_order_schedule_snapshot_contract_no",
    ]:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="order_schedule_snapshot")
