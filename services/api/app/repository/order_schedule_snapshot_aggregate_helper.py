from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, case, cast, extract, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc


class OrderScheduleSnapshotAggregateHelper:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_summary(self) -> dict[str, Any]:
        planned_end_year = cast(extract("year", OrderScheduleSnapshot.planned_end_date), Integer)
        planned_end_month = cast(extract("month", OrderScheduleSnapshot.planned_end_date), Integer)
        grouped_stmt = union_all(
            select(
                literal("summary").label("bucket"),
                literal(None).cast(String).label("group_key"),
                literal(None).cast(Integer).label("year_part"),
                literal(None).cast(Integer).label("month_part"),
                func.count(OrderScheduleSnapshot.id).label("item_count"),
                func.sum(case((OrderScheduleSnapshot.schedule_status == "scheduled", 1), else_=0)).label("metric_one"),
                func.sum(case((OrderScheduleSnapshot.warning_level == "abnormal", 1), else_=0)).label("metric_two"),
            ),
            select(
                literal("status").label("bucket"),
                OrderScheduleSnapshot.schedule_status.label("group_key"),
                literal(None).cast(Integer).label("year_part"),
                literal(None).cast(Integer).label("month_part"),
                func.count(OrderScheduleSnapshot.id).label("item_count"),
                literal(None).cast(Integer).label("metric_one"),
                literal(None).cast(Integer).label("metric_two"),
            ).group_by(OrderScheduleSnapshot.schedule_status),
            select(
                literal("planned_end_month").label("bucket"),
                literal(None).cast(String).label("group_key"),
                planned_end_year.label("year_part"),
                planned_end_month.label("month_part"),
                func.count(OrderScheduleSnapshot.id).label("item_count"),
                literal(None).cast(Integer).label("metric_one"),
                literal(None).cast(Integer).label("metric_two"),
            )
            .where(OrderScheduleSnapshot.planned_end_date.isnot(None))
            .group_by(planned_end_year, planned_end_month),
        )
        grouped_rows = (await self.session.execute(grouped_stmt)).all()

        total_orders = 0
        scheduled_orders = 0
        abnormal_orders = 0
        status_counts: list[tuple[str, int]] = []
        planned_end_month_counts: list[tuple[str, int]] = []
        for bucket, group_key, year_part, month_part, item_count, metric_one, metric_two in grouped_rows:
            count = int(item_count or 0)
            if bucket == "summary":
                total_orders = count
                scheduled_orders = int(metric_one or 0)
                abnormal_orders = int(metric_two or 0)
            elif bucket == "status" and group_key:
                status_counts.append((group_key, count))
            elif bucket == "planned_end_month" and year_part is not None and month_part is not None:
                planned_end_month_counts.append((f"{int(year_part):04d}-{int(month_part):02d}", count))

        status_counts.sort(key=lambda item: item[0])
        planned_end_month_counts.sort(key=lambda item: item[0])
        return {
            "total_orders": total_orders,
            "scheduled_orders": scheduled_orders,
            "abnormal_orders": abnormal_orders,
            "status_counts": status_counts,
            "planned_end_month_counts": planned_end_month_counts,
        }

    async def summarize_business_groups(self, *, limit: int | None = None) -> list[tuple[str, int, Any]]:
        normalized_group = func.coalesce(func.nullif(func.trim(OrderScheduleSnapshot.business_group), ""), "未分组")
        stmt = (
            select(
                normalized_group.label("business_group"),
                func.count(OrderScheduleSnapshot.id).label("order_count"),
                func.coalesce(func.sum(OrderScheduleSnapshot.line_total_amount), 0).label("total_amount"),
            )
            .group_by(normalized_group)
            .order_by(
                func.count(OrderScheduleSnapshot.id).desc(),
                func.coalesce(func.sum(OrderScheduleSnapshot.line_total_amount), 0).desc(),
                normalized_group.asc(),
            )
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [(group, int(order_count or 0), total_amount or 0) for group, order_count, total_amount in result.all()]

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(OrderScheduleSnapshot)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_by_schedule_status(self) -> list[tuple[str, int]]:
        stmt = (
            select(OrderScheduleSnapshot.schedule_status, func.count())
            .group_by(OrderScheduleSnapshot.schedule_status)
            .order_by(OrderScheduleSnapshot.schedule_status)
        )
        result = await self.session.execute(stmt)
        return [(status, count) for status, count in result.all() if status]

    async def count_by_warning_level(self) -> list[tuple[str, int]]:
        stmt = (
            select(OrderScheduleSnapshot.warning_level, func.count())
            .where(OrderScheduleSnapshot.warning_level.isnot(None))
            .group_by(OrderScheduleSnapshot.warning_level)
            .order_by(OrderScheduleSnapshot.warning_level)
        )
        result = await self.session.execute(stmt)
        return [(level, count) for level, count in result.all() if level]

    async def count_by_refresh_source(self) -> list[tuple[str, int]]:
        stmt = (
            select(OrderScheduleSnapshot.last_refresh_source, func.count())
            .group_by(OrderScheduleSnapshot.last_refresh_source)
            .order_by(OrderScheduleSnapshot.last_refresh_source)
        )
        result = await self.session.execute(stmt)
        return [(source, count) for source, count in result.all() if source]

    async def get_refresh_bounds(self) -> tuple[datetime | None, datetime | None]:
        stmt = select(
            func.min(OrderScheduleSnapshot.refreshed_at),
            func.max(OrderScheduleSnapshot.refreshed_at),
        )
        oldest, latest = (await self.session.execute(stmt)).one()
        return oldest, latest

    async def get_observability_aggregates(self) -> dict[str, Any]:
        known_order_count = select(func.count()).select_from(self.known_order_line_ids_subquery()).scalar_subquery()
        aggregate_stmt = select(
            known_order_count.label("known_order_count"),
            func.count().label("total_snapshots"),
            func.min(OrderScheduleSnapshot.refreshed_at).label("oldest_refreshed_at"),
            func.max(OrderScheduleSnapshot.refreshed_at).label("latest_refreshed_at"),
        )
        aggregate_row = (await self.session.execute(aggregate_stmt)).one()

        grouped_stmt = union_all(
            select(
                literal("status").label("bucket"),
                OrderScheduleSnapshot.schedule_status.label("group_key"),
                func.count().label("item_count"),
            ).group_by(OrderScheduleSnapshot.schedule_status),
            select(
                literal("refresh_source").label("bucket"),
                OrderScheduleSnapshot.last_refresh_source.label("group_key"),
                func.count().label("item_count"),
            )
            .where(OrderScheduleSnapshot.last_refresh_source.isnot(None))
            .group_by(OrderScheduleSnapshot.last_refresh_source),
        )
        grouped_rows = (await self.session.execute(grouped_stmt)).all()

        status_counts: dict[str, int] = {}
        refresh_source_counts: dict[str, int] = {}
        for bucket, group_key, item_count in grouped_rows:
            if not group_key:
                continue
            target = status_counts if bucket == "status" else refresh_source_counts
            target[str(group_key)] = int(item_count or 0)

        return {
            "known_order_count": int(aggregate_row.known_order_count or 0),
            "total_snapshots": int(aggregate_row.total_snapshots or 0),
            "oldest_refreshed_at": aggregate_row.oldest_refreshed_at,
            "latest_refreshed_at": aggregate_row.latest_refreshed_at,
            "status_counts": status_counts,
            "refresh_source_counts": refresh_source_counts,
        }

    async def count_by_planned_end_month(self) -> list[tuple[str, int]]:
        year_part = extract("year", OrderScheduleSnapshot.planned_end_date)
        month_part = extract("month", OrderScheduleSnapshot.planned_end_date)
        stmt = (
            select(
                year_part.label("year_part"),
                month_part.label("month_part"),
                func.count(OrderScheduleSnapshot.id).label("order_count"),
            )
            .where(OrderScheduleSnapshot.planned_end_date.isnot(None))
            .group_by(year_part, month_part)
            .order_by(year_part, month_part)
        )
        result = await self.session.execute(stmt)
        return [
            (f"{int(year):04d}-{int(month):02d}", int(count or 0))
            for year, month, count in result.all()
            if year is not None and month is not None
        ]

    @staticmethod
    def known_order_line_ids_subquery():
        sales_stmt = select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.id.is_not(None)
        )
        machine_stmt = select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.order_line_id.is_not(None)
        )
        return sales_stmt.union(machine_stmt).subquery()
