from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from sqlalchemy import distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bom_relation import BomRelationSrc
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.services.schedule_snapshot_refresh_seed_helper import ScheduleSnapshotRefreshSeedHelper


class ScheduleSnapshotRefreshTargetResolver:
    """Resolve snapshot refresh target order-line ids for different trigger types."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        seed_helper: ScheduleSnapshotRefreshSeedHelper,
    ):
        self.session = session
        self.seed_helper = seed_helper

    async def list_order_line_ids_by_material_no(self, material_no: str) -> list[int]:
        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.material_no == material_no
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.material_no == material_no
        )
        return await self.seed_helper.merge_order_line_ids(sales_stmt, machine_stmt)

    async def list_order_line_ids_by_product_models(self, product_models: Sequence[str]) -> list[int]:
        models = [model for model in dict.fromkeys(product_models) if model]
        if not models:
            return []
        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.product_model.in_(models)
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.product_model.in_(models)
        )
        return await self.seed_helper.merge_order_line_ids(sales_stmt, machine_stmt)

    async def list_order_line_ids_by_bom_component_no(
        self,
        bom_component_no: str,
        *,
        machine_model: str | None = None,
    ) -> list[int]:
        if not bom_component_no:
            return []
        machine_material_subquery = (
            select(distinct(BomRelationSrc.machine_material_no).label("machine_material_no"))
            .where(
                BomRelationSrc.bom_component_no == bom_component_no,
            )
            .subquery()
        )

        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.material_no.in_(select(machine_material_subquery.c.machine_material_no))
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.material_no.in_(select(machine_material_subquery.c.machine_material_no))
        )
        if machine_model:
            sales_stmt = sales_stmt.where(SalesPlanOrderLineSrc.product_model == machine_model)
            machine_stmt = machine_stmt.where(MachineScheduleResult.product_model == machine_model)
        return await self.seed_helper.merge_order_line_ids(sales_stmt, machine_stmt)

    async def list_order_line_ids_by_part_type(
        self,
        part_type: str,
        *,
        machine_model: str | None = None,
        plant: str | None = None,
    ) -> list[int]:
        if not part_type:
            return []
        machine_material_stmt = select(distinct(BomRelationSrc.machine_material_no).label("machine_material_no")).where(
            BomRelationSrc.bom_component_desc.is_not(None),
            BomRelationSrc.bom_component_desc.startswith(part_type),
        )
        if plant:
            machine_material_stmt = machine_material_stmt.where(BomRelationSrc.plant == plant)
        machine_material_subquery = machine_material_stmt.subquery()

        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.material_no.in_(select(machine_material_subquery.c.machine_material_no))
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.material_no.in_(select(machine_material_subquery.c.machine_material_no))
        )
        if machine_model:
            sales_stmt = sales_stmt.where(SalesPlanOrderLineSrc.product_model == machine_model)
            machine_stmt = machine_stmt.where(MachineScheduleResult.product_model == machine_model)
        if plant:
            sales_stmt = sales_stmt.where(SalesPlanOrderLineSrc.delivery_plant == plant)
            machine_stmt = machine_stmt.where(MachineScheduleResult.delivery_plant == plant)
        return await self.seed_helper.merge_order_line_ids(sales_stmt, machine_stmt)

    async def list_order_line_ids_in_future_window(
        self,
        *,
        today: date,
        window_days: int | None,
    ) -> tuple[int, list[int]]:
        days = window_days or settings.snapshot_refresh_window_days
        cutoff = datetime.combine(today - timedelta(days=days), time.min)
        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            or_(
                SalesPlanOrderLineSrc.confirmed_delivery_date.is_(None),
                SalesPlanOrderLineSrc.confirmed_delivery_date >= cutoff,
            )
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            or_(
                MachineScheduleResult.confirmed_delivery_date.is_(None),
                MachineScheduleResult.confirmed_delivery_date >= cutoff,
            )
        )
        order_line_ids = await self.seed_helper.merge_order_line_ids(sales_stmt, machine_stmt)
        return days, order_line_ids
