"""add bom relation compound indexes

Revision ID: 20260320_0002
Revises: 20260320_0001
Create Date: 2026-03-20 00:00:02
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260320_0002"
down_revision = "20260320_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bom_machine_material_material_no "
        "ON bom_relation_src (machine_material_no, material_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bom_machine_material_component_no "
        "ON bom_relation_src (machine_material_no, bom_component_no)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_bom_machine_material_component_no")
    op.execute("DROP INDEX IF EXISTS idx_bom_machine_material_material_no")
