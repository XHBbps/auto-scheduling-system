from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import distinct, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.data_issue_repo import DataIssueRepo
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.scheduler.schedule_check_service import ScheduleCheckService


class ScheduleSnapshotRefreshContextLoader:
    """Shared loaders for snapshot refresh batching and dynamic context assembly."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        today: date,
        check_service: ScheduleCheckService,
        machine_repo: MachineScheduleResultRepo,
        issue_repo: DataIssueRepo,
    ):
        self.session = session
        self.today = today
        self.check_service = check_service
        self.machine_repo = machine_repo
        self.issue_repo = issue_repo

    async def load_sales_orders_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, SalesPlanOrderLineSrc]:
        if not order_line_ids:
            return {}
        stmt = select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.id.in_(order_line_ids))
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.id: row for row in rows if row.id is not None}

    async def load_machine_results_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, MachineScheduleResult]:
        rows = await self.machine_repo.find_by_order_line_ids(order_line_ids)
        return {row.order_line_id: row for row in rows if row.order_line_id is not None}

    async def load_open_issue_map_for_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, list[DataIssueRecord]]:
        rows = await self.issue_repo.list_open_by_order_line_ids(order_line_ids)
        grouped: dict[int, list[DataIssueRecord]] = {}
        for row in rows:
            order_line_id = row.order_line_id
            if order_line_id is None:
                continue
            grouped.setdefault(order_line_id, []).append(row)
        return grouped

    async def load_open_issue_map(self) -> dict[int, list[DataIssueRecord]]:
        stmt = select(DataIssueRecord).where(DataIssueRecord.status == "open")
        rows = (await self.session.execute(stmt)).scalars().all()
        grouped: dict[int, list[DataIssueRecord]] = {}
        for row in rows:
            try:
                order_line_id = int(row.biz_key) if row.biz_key is not None else None
            except (TypeError, ValueError):
                order_line_id = None
            if order_line_id is None:
                continue
            grouped.setdefault(order_line_id, []).append(row)
        return grouped

    async def load_machine_bom_pairs(self) -> set[tuple[str, str]]:
        stmt = select(
            distinct(BomRelationSrc.machine_material_no),
            func.coalesce(BomRelationSrc.plant, literal(settings.default_plant)).label("plant"),
        ).where(BomRelationSrc.machine_material_no.isnot(None))
        rows = (await self.session.execute(stmt)).all()
        return {(str(material_no), str(plant)) for material_no, plant in rows if material_no}

    async def build_dynamic_context(
        self,
        *,
        sales_orders: Sequence[SalesPlanOrderLineSrc],
        machine_rows: Sequence[MachineScheduleResult],
    ) -> dict[str, Any]:
        return {
            "bom_material_pairs": await self.load_machine_bom_pairs(),
            "baselines_by_model": await self.load_machine_cycle_baselines(),
            "calendar": await self.load_seed_calendar(
                list(sales_orders),
                list(machine_rows),
            ),
        }

    async def build_shared_dynamic_context_for_known_orders(self) -> dict[str, Any]:
        max_delivery_date = await self.load_known_order_max_delivery_date()
        return {
            "bom_material_pairs": await self.load_machine_bom_pairs(),
            "baselines_by_model": await self.load_machine_cycle_baselines(),
            "calendar": await self.load_calendar_until(max_delivery_date),
        }

    async def load_machine_cycle_baselines(self) -> dict[str, list[MachineCycleBaseline]]:
        stmt = (
            select(MachineCycleBaseline)
            .where(MachineCycleBaseline.is_active == True)
            .order_by(
                MachineCycleBaseline.machine_model.asc(),
                MachineCycleBaseline.order_qty.asc(),
                MachineCycleBaseline.sample_count.desc(),
                MachineCycleBaseline.updated_at.desc(),
                MachineCycleBaseline.id.desc(),
            )
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        grouped: dict[str, dict[Decimal, MachineCycleBaseline]] = {}
        for row in rows:
            if not row.machine_model:
                continue
            grouped.setdefault(row.machine_model, {})
            grouped[row.machine_model].setdefault(row.order_qty, row)
        return {
            machine_model: [bucket[qty] for qty in sorted(bucket.keys())] for machine_model, bucket in grouped.items()
        }

    async def load_seed_calendar(
        self,
        sales_orders: Sequence[SalesPlanOrderLineSrc],
        machine_rows: Sequence[MachineScheduleResult],
    ) -> dict[date, bool]:
        end_dates: list[date] = []
        for row in list(sales_orders) + list(machine_rows):
            delivery = getattr(row, "confirmed_delivery_date", None)
            if isinstance(delivery, datetime):
                end_dates.append(delivery.date())
            elif isinstance(delivery, date):
                end_dates.append(delivery)
        end = max(end_dates, default=self.today) + timedelta(days=30)
        return await self.load_calendar_until(end)

    async def load_known_order_max_delivery_date(self) -> date:
        stmt = select(
            select(func.max(SalesPlanOrderLineSrc.confirmed_delivery_date))
            .scalar_subquery()
            .label("sales_max_delivery"),
            select(func.max(MachineScheduleResult.confirmed_delivery_date))
            .scalar_subquery()
            .label("machine_max_delivery"),
        )
        row = (await self.session.execute(stmt)).one()
        candidates = [
            self.normalize_date_value(row.sales_max_delivery),
            self.normalize_date_value(row.machine_max_delivery),
        ]
        return max((value for value in candidates if value is not None), default=self.today)

    async def load_calendar_until(self, end_date: date | datetime | None) -> dict[date, bool]:
        normalized_end = self.normalize_date_value(end_date) or self.today
        start = self.today - timedelta(days=30)
        end = normalized_end + timedelta(days=30)
        return await self.check_service.calendar_repo.get_calendar_map(start, end)

    @staticmethod
    def normalize_date_value(value: date | datetime | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value
