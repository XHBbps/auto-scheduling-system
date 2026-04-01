"""extend part cycle baseline with plant and history governance

Revision ID: 20260326_0015
Revises: 20260326_0014
Create Date: 2026-03-26 00:15:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260326_0015"
down_revision = "20260326_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("part_cycle_baseline") as batch_op:
        batch_op.add_column(sa.Column("plant", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("source_updated_at", sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_pcb_material_machine_plant",
            ["material_no", "machine_model", "plant"],
        )
        batch_op.create_index("idx_pcb_plant", ["plant"], unique=False)
        batch_op.create_index("idx_pcb_source_active", ["cycle_source", "is_active"], unique=False)

    op.create_index(
        "uq_pcb_material_machine_null_plant",
        "part_cycle_baseline",
        ["material_no", "machine_model"],
        unique=True,
        postgresql_where=sa.text("plant IS NULL"),
        sqlite_where=sa.text("plant IS NULL"),
    )

    with op.batch_alter_table("part_cycle_baseline") as batch_op:
        batch_op.alter_column("sample_count", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_pcb_material_machine_null_plant", table_name="part_cycle_baseline")

    with op.batch_alter_table("part_cycle_baseline") as batch_op:
        batch_op.drop_index("idx_pcb_source_active")
        batch_op.drop_index("idx_pcb_plant")
        batch_op.drop_constraint("uq_pcb_material_machine_plant", type_="unique")
        batch_op.drop_column("source_updated_at")
        batch_op.drop_column("sample_count")
        batch_op.drop_column("plant")
