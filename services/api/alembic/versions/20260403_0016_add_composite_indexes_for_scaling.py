"""add composite indexes for 120w+ part_schedule_result scaling

Revision ID: 20260403_0016
Revises: 20260326_0015
Create Date: 2026-04-03 00:16:00
"""
from __future__ import annotations

from alembic import op

revision = "20260403_0016"
down_revision = "20260326_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- part_schedule_result (target: 120w rows / 5 years) ---

    # 排产详情页：按订单+部装查零件
    op.create_index(
        "idx_psr_order_assembly",
        "part_schedule_result",
        ["order_line_id", "assembly_name"],
        if_not_exists=True,
    )

    # 日历/Dashboard：按时间范围查开工计划
    op.create_index(
        "idx_psr_planned_dates",
        "part_schedule_result",
        ["planned_start_date", "planned_end_date"],
        if_not_exists=True,
    )

    # 零件维度：按物料号查跨订单排产
    op.create_index(
        "idx_psr_part_material",
        "part_schedule_result",
        ["part_material_no", "planned_start_date"],
        if_not_exists=True,
    )

    # Dashboard 异常统计聚合
    op.create_index(
        "idx_psr_warning_level",
        "part_schedule_result",
        ["warning_level"],
        if_not_exists=True,
    )

    # --- order_schedule_snapshot (target: 3w rows / 5 years) ---

    # 排产列表首页：状态+交期组合筛选
    op.create_index(
        "idx_snapshot_status_delivery",
        "order_schedule_snapshot",
        ["schedule_status", "confirmed_delivery_date"],
        if_not_exists=True,
    )

    # 按产品系列+机型筛选
    op.create_index(
        "idx_snapshot_product_series_model",
        "order_schedule_snapshot",
        ["product_series", "product_model"],
        if_not_exists=True,
    )

    # Dashboard 风险筛选（异常+未排产组合）
    op.create_index(
        "idx_snapshot_warning_status",
        "order_schedule_snapshot",
        ["warning_level", "schedule_status"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_snapshot_warning_status", table_name="order_schedule_snapshot", if_exists=True)
    op.drop_index("idx_snapshot_product_series_model", table_name="order_schedule_snapshot", if_exists=True)
    op.drop_index("idx_snapshot_status_delivery", table_name="order_schedule_snapshot", if_exists=True)
    op.drop_index("idx_psr_warning_level", table_name="part_schedule_result", if_exists=True)
    op.drop_index("idx_psr_part_material", table_name="part_schedule_result", if_exists=True)
    op.drop_index("idx_psr_planned_dates", table_name="part_schedule_result", if_exists=True)
    op.drop_index("idx_psr_order_assembly", table_name="part_schedule_result", if_exists=True)
