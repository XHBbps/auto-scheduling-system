"""add recursive part schedule fields

Revision ID: 20260323_0007
Revises: 20260323_0006
Create Date: 2026-03-23 00:00:07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260323_0007"
down_revision = "20260323_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("part_schedule_result"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("part_schedule_result")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("part_schedule_result")}

    column_defs = [
        ("parent_material_no", sa.String(length=100), True),
        ("parent_name", sa.String(length=255), True),
        ("node_level", sa.Integer(), True),
        ("bom_path", sa.Text(), True),
        ("bom_path_key", sa.String(length=500), True),
    ]
    for name, column_type, nullable in column_defs:
        if name not in existing_columns:
            op.add_column("part_schedule_result", sa.Column(name, column_type, nullable=nullable))

    for index_name, columns in [
        ("idx_psr_parent_material_no", ["parent_material_no"]),
        ("idx_psr_bom_path_key", ["bom_path_key"]),
    ]:
        if index_name not in existing_indexes:
            op.create_index(index_name, "part_schedule_result", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("part_schedule_result"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("part_schedule_result")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("part_schedule_result")}

    for index_name in [
        "idx_psr_bom_path_key",
        "idx_psr_parent_material_no",
    ]:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="part_schedule_result")

    for column_name in [
        "bom_path_key",
        "bom_path",
        "node_level",
        "parent_name",
        "parent_material_no",
    ]:
        if column_name in existing_columns:
            op.drop_column("part_schedule_result", column_name)
