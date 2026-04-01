"""add pg_trgm search indexes

Revision ID: 20260326_0014
Revises: 20260326_0013
Create Date: 2026-03-26 00:00:14
"""
from __future__ import annotations

from alembic import op

revision = "20260326_0014"
down_revision = "20260326_0013"
branch_labels = None
depends_on = None


TRIGRAM_INDEX_SQL = {
    "idx_oss_contract_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_oss_contract_no_trgm
        ON order_schedule_snapshot USING gin (contract_no gin_trgm_ops)
    """,
    "idx_oss_customer_name_trgm": """
        CREATE INDEX IF NOT EXISTS idx_oss_customer_name_trgm
        ON order_schedule_snapshot USING gin (customer_name gin_trgm_ops)
    """,
    "idx_oss_product_model_trgm": """
        CREATE INDEX IF NOT EXISTS idx_oss_product_model_trgm
        ON order_schedule_snapshot USING gin (product_model gin_trgm_ops)
    """,
    "idx_oss_order_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_oss_order_no_trgm
        ON order_schedule_snapshot USING gin (order_no gin_trgm_ops)
    """,
    "idx_psr_part_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_psr_part_material_no_trgm
        ON part_schedule_result USING gin (part_material_no gin_trgm_ops)
    """,
    "idx_psr_key_part_name_trgm": """
        CREATE INDEX IF NOT EXISTS idx_psr_key_part_name_trgm
        ON part_schedule_result USING gin (key_part_name gin_trgm_ops)
    """,
    "idx_psr_key_part_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_psr_key_part_material_no_trgm
        ON part_schedule_result USING gin (key_part_material_no gin_trgm_ops)
    """,
    "idx_splo_contract_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_contract_no_trgm
        ON sales_plan_order_line_src USING gin (contract_no gin_trgm_ops)
    """,
    "idx_splo_customer_name_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_customer_name_trgm
        ON sales_plan_order_line_src USING gin (customer_name gin_trgm_ops)
    """,
    "idx_splo_product_series_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_product_series_trgm
        ON sales_plan_order_line_src USING gin (product_series gin_trgm_ops)
    """,
    "idx_splo_product_model_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_product_model_trgm
        ON sales_plan_order_line_src USING gin (product_model gin_trgm_ops)
    """,
    "idx_splo_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_material_no_trgm
        ON sales_plan_order_line_src USING gin (material_no gin_trgm_ops)
    """,
    "idx_splo_business_group_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_business_group_trgm
        ON sales_plan_order_line_src USING gin (business_group gin_trgm_ops)
    """,
    "idx_splo_sales_branch_company_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_sales_branch_company_trgm
        ON sales_plan_order_line_src USING gin (sales_branch_company gin_trgm_ops)
    """,
    "idx_splo_sales_sub_branch_trgm": """
        CREATE INDEX IF NOT EXISTS idx_splo_sales_sub_branch_trgm
        ON sales_plan_order_line_src USING gin (sales_sub_branch gin_trgm_ops)
    """,
    "idx_bom_machine_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_bom_machine_material_no_trgm
        ON bom_relation_src USING gin (machine_material_no gin_trgm_ops)
    """,
    "idx_bom_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_bom_material_no_trgm
        ON bom_relation_src USING gin (material_no gin_trgm_ops)
    """,
    "idx_bom_component_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_bom_component_no_trgm
        ON bom_relation_src USING gin (bom_component_no gin_trgm_ops)
    """,
    "idx_bom_part_type_trgm": """
        CREATE INDEX IF NOT EXISTS idx_bom_part_type_trgm
        ON bom_relation_src USING gin (part_type gin_trgm_ops)
    """,
    "idx_prod_order_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_prod_order_no_trgm
        ON production_order_history_src USING gin (production_order_no gin_trgm_ops)
    """,
    "idx_prod_material_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_prod_material_no_trgm
        ON production_order_history_src USING gin (material_no gin_trgm_ops)
    """,
    "idx_prod_machine_model_trgm": """
        CREATE INDEX IF NOT EXISTS idx_prod_machine_model_trgm
        ON production_order_history_src USING gin (machine_model gin_trgm_ops)
    """,
    "idx_mch_machine_model_trgm": """
        CREATE INDEX IF NOT EXISTS idx_mch_machine_model_trgm
        ON machine_cycle_history_src USING gin (machine_model gin_trgm_ops)
    """,
    "idx_mch_product_series_trgm": """
        CREATE INDEX IF NOT EXISTS idx_mch_product_series_trgm
        ON machine_cycle_history_src USING gin (product_series gin_trgm_ops)
    """,
    "idx_mch_contract_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_mch_contract_no_trgm
        ON machine_cycle_history_src USING gin (contract_no gin_trgm_ops)
    """,
    "idx_mch_order_no_trgm": """
        CREATE INDEX IF NOT EXISTS idx_mch_order_no_trgm
        ON machine_cycle_history_src USING gin (order_no gin_trgm_ops)
    """,
}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for sql in TRIGRAM_INDEX_SQL.values():
        op.execute(sql)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for index_name in reversed(list(TRIGRAM_INDEX_SQL.keys())):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
