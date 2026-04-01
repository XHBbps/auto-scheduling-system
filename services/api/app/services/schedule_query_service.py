from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dirty_text_utils import normalize_legacy_issue_detail
from app.repository.data_issue_repo import DataIssueRepo
from app.repository.order_schedule_snapshot_repo import OrderScheduleSnapshotRepo
from app.repository.part_schedule_result_repo import PartScheduleResultRepo
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService


class ScheduleQueryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.snapshot_repo = OrderScheduleSnapshotRepo(session)
        self.psr_repo = PartScheduleResultRepo(session)
        self.issue_repo = DataIssueRepo(session)
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session)

    @staticmethod
    def _parse_page_int(value: Any, default: int) -> int:
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_legacy_issue_text(value: str | None) -> str | None:
        return normalize_legacy_issue_detail(value)

    def _serialize_issue(self, issue: Any) -> dict[str, Any]:
        payload = {column.key: getattr(issue, column.key) for column in issue.__table__.columns}
        payload["issue_detail"] = self._normalize_legacy_issue_text(payload.get("issue_detail"))
        return payload

    async def ensure_snapshots_ready(self) -> None:
        await self.snapshot_refresh_service.ensure_seeded(
            source="query_service",
            reason="lazy_snapshot_seed",
        )

    async def list_product_series_options(self) -> list[str]:
        await self.ensure_snapshots_ready()
        return await self.snapshot_repo.list_distinct_product_series()

    async def list_schedules(self, **filters: Any) -> dict[str, Any]:
        await self.ensure_snapshots_ready()
        page_no = self._parse_page_int(filters.pop("page_no", 1), 1)
        page_size = self._parse_page_int(filters.pop("page_size", 20), 20)
        items, total = await self.snapshot_repo.paginate(
            page_no=page_no,
            page_size=page_size,
            **filters,
        )
        return {
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": items,
        }

    async def list_part_schedules(self, **filters: Any) -> dict[str, Any]:
        await self.ensure_snapshots_ready()
        page_no = self._parse_page_int(filters.pop("page_no", 1), 1)
        page_size = self._parse_page_int(filters.pop("page_size", 20), 20)
        rows, total = await self.psr_repo.paginate(
            page_no=page_no,
            page_size=page_size,
            **filters,
        )

        enriched = []
        for item, snapshot in rows:
            payload = {column.key: getattr(item, column.key) for column in item.__table__.columns}
            payload["contract_no"] = snapshot.contract_no if snapshot else None
            payload["customer_name"] = snapshot.customer_name if snapshot else None
            payload["product_series"] = snapshot.product_series if snapshot else None
            payload["product_model"] = snapshot.product_model if snapshot else None
            payload["product_name"] = snapshot.product_name if snapshot else None
            payload["material_no"] = snapshot.material_no if snapshot else None
            payload["plant"] = snapshot.plant if snapshot else None
            payload["quantity"] = snapshot.quantity if snapshot else None
            payload["order_type"] = snapshot.order_type if snapshot else None
            payload["custom_no"] = snapshot.custom_no if snapshot else None
            payload["business_group"] = snapshot.business_group if snapshot else None
            payload["sales_person_name"] = snapshot.sales_person_name if snapshot else None
            payload["sales_branch_company"] = snapshot.sales_branch_company if snapshot else None
            payload["sales_sub_branch"] = snapshot.sales_sub_branch if snapshot else None
            payload["order_no"] = snapshot.order_no if snapshot else None
            payload["order_date"] = snapshot.order_date if snapshot else None
            payload["confirmed_delivery_date"] = snapshot.confirmed_delivery_date if snapshot else None
            payload["line_total_amount"] = snapshot.line_total_amount if snapshot else None
            enriched.append(payload)

        return {
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": enriched,
        }

    async def get_detail(self, order_line_id: int) -> dict[str, Any] | None:
        await self.ensure_snapshots_ready()
        snapshot = await self.snapshot_repo.find_by_order_line_id(order_line_id)
        if not snapshot:
            snapshot = await self.snapshot_refresh_service.refresh_one_committed(
                order_line_id,
                source="query_service",
                reason="detail_on_demand_refresh",
            )
            if snapshot:
                snapshot = await self.snapshot_repo.find_by_order_line_id(order_line_id) or snapshot
        if not snapshot:
            return None

        parts = await self.psr_repo.find_by_order_line_id(order_line_id)
        issues, _ = await self.issue_repo.paginate(
            page_no=1,
            page_size=100,
            order_line_id=order_line_id,
        )
        return {
            "machine_schedule": snapshot,
            "part_schedules": list(parts),
            "issues": [self._serialize_issue(issue) for issue in issues],
        }

    async def get_dashboard_overview(self) -> dict[str, Any]:
        await self.ensure_snapshots_ready()

        machine_dashboard_summary = await self.snapshot_repo.get_dashboard_summary()
        total_orders = machine_dashboard_summary["total_orders"]
        status_counts_raw = machine_dashboard_summary["status_counts"]
        status_counts = [{"key": status, "count": count} for status, count in status_counts_raw]
        scheduled_orders = machine_dashboard_summary["scheduled_orders"]
        unscheduled_orders = max(total_orders - scheduled_orders, 0)
        abnormal_orders = machine_dashboard_summary["abnormal_orders"]

        planned_end_month_counts = [
            {"key": month, "count": count}
            for month, count in machine_dashboard_summary["planned_end_month_counts"]
        ]

        warning_orders = await self.snapshot_repo.list_warning_orders(limit=10)
        abnormal_machine_orders = await self.snapshot_repo.list_abnormal_orders(limit=50)

        today = date.today()

        planned_end_day_raw = await self.snapshot_repo.aggregate_quantity_by_day(
            "planned_end_date", today - timedelta(days=14), today + timedelta(days=15),
        )
        planned_end_day_counts = [
            {"key": day.isoformat(), "count": int(data.get("order_count", 0))}
            for day, data in sorted(planned_end_day_raw.items())
        ]
        business_group_summary = [
            {
                "business_group": business_group,
                "order_count": order_count,
                "total_amount": total_amount,
            }
            for business_group, order_count, total_amount in await self.snapshot_repo.summarize_business_groups(limit=8)
        ]
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        month_start = today.replace(day=1)
        month_end = _shift_month(month_start, 1)
        delivery_risk_window_end = today + timedelta(days=31)

        time_summaries = await self.snapshot_repo.summarize_date_field_windows(
            "confirmed_delivery_date",
            [
                ("today", today, today + timedelta(days=1)),
                ("week", week_start, week_end),
                ("month", month_start, month_end),
            ],
        )
        today_summary = time_summaries["today"]
        week_summary = time_summaries["week"]
        month_summary = time_summaries["month"]
        delivery_risk_orders = await self.snapshot_repo.list_delivery_risk_orders(
            today,
            delivery_risk_window_end,
            limit=20,
        )
        delivery_trends = await self._build_dashboard_delivery_trends(today)

        part_dashboard_summary = await self.psr_repo.get_dashboard_summary(top_assembly_limit=10)
        total_parts = part_dashboard_summary["total_parts"]
        abnormal_parts = part_dashboard_summary["abnormal_parts"]
        warning_counts = [
            {"key": level, "count": count}
            for level, count in part_dashboard_summary["warning_counts"]
        ]
        top_assemblies = [
            {"assembly_name": assembly_name, "count": count}
            for assembly_name, count in part_dashboard_summary["top_assemblies"]
        ]

        return {
            "machine_summary": {
                "total_orders": total_orders,
                "scheduled_orders": scheduled_orders,
                "unscheduled_orders": unscheduled_orders,
                "abnormal_orders": abnormal_orders,
                "status_counts": status_counts,
                "planned_end_month_counts": planned_end_month_counts,
                "planned_end_day_counts": planned_end_day_counts,
                "warning_orders": list(warning_orders),
            },
            "part_summary": {
                "total_parts": total_parts,
                "abnormal_parts": abnormal_parts,
                "warning_counts": warning_counts,
                "top_assemblies": top_assemblies,
            },
            "today_summary": today_summary,
            "week_summary": week_summary,
            "month_summary": month_summary,
            "delivery_trends": delivery_trends,
            "business_group_summary": business_group_summary,
            "abnormal_machine_orders": list(abnormal_machine_orders),
            "delivery_risk_orders": list(delivery_risk_orders),
        }

    async def _build_dashboard_delivery_trends(self, today: date) -> dict[str, list[dict[str, int | str]]]:
        day_start = today - timedelta(days=29)
        day_end = today + timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        first_week_start = week_start - timedelta(weeks=11)
        week_end = week_start + timedelta(days=7)
        month_start = today.replace(day=1)
        first_month_start = _shift_month(month_start, -11)
        month_end = _shift_month(month_start, 1)

        daily_scheduled = await self.snapshot_repo.aggregate_quantity_by_day("planned_start_date", day_start, day_end)
        daily_delivery = await self.snapshot_repo.aggregate_quantity_by_day("confirmed_delivery_date", day_start, day_end)
        weekly_scheduled = await self.snapshot_repo.aggregate_quantity_by_day("planned_start_date", first_week_start, week_end)
        weekly_delivery = await self.snapshot_repo.aggregate_quantity_by_day("confirmed_delivery_date", first_week_start, week_end)
        monthly_scheduled = await self.snapshot_repo.aggregate_quantity_by_day("planned_start_date", first_month_start, month_end)
        monthly_delivery = await self.snapshot_repo.aggregate_quantity_by_day("confirmed_delivery_date", first_month_start, month_end)

        return {
            "day": _build_day_trend_points(day_start, 30, daily_scheduled, daily_delivery),
            "week": _build_week_trend_points(first_week_start, 12, weekly_scheduled, weekly_delivery),
            "month": _build_month_trend_points(first_month_start, 12, monthly_scheduled, monthly_delivery),
        }

    @staticmethod
    def _zero_quantity() -> Decimal:
        return Decimal("0")

    async def get_schedule_calendar_distribution(self, year: int, month: int) -> list[dict[str, Any]]:
        await self.ensure_snapshots_ready()

        month_start = date(year, month, 1)
        month_end = _shift_month(month_start, 1)

        distribution_map = await self.snapshot_repo.aggregate_calendar_distribution(
            month_start,
            month_end,
        )

        items: list[dict[str, Any]] = []
        current = month_start
        while current < month_end:
            summary = distribution_map.get(current, {})
            items.append({
                "calendar_date": current,
                "delivery_order_count": int(summary.get("delivery_order_count", 0)),
                "delivery_quantity_sum": summary.get("delivery_quantity_sum", self._zero_quantity()),
                "trigger_order_count": int(summary.get("trigger_order_count", 0)),
                "trigger_quantity_sum": summary.get("trigger_quantity_sum", self._zero_quantity()),
                "planned_start_order_count": int(summary.get("planned_start_order_count", 0)),
                "planned_start_quantity_sum": summary.get("planned_start_quantity_sum", self._zero_quantity()),
            })
            current = current.fromordinal(current.toordinal() + 1)

        return items

    async def get_schedule_calendar_day_detail(self, target_date: date) -> dict[str, Any]:
        await self.ensure_snapshots_ready()
        return await self.snapshot_repo.get_calendar_day_detail(target_date)


def _shift_month(value: date, months: int) -> date:
    total_month = (value.year * 12 + (value.month - 1)) + months
    year = total_month // 12
    month = total_month % 12 + 1
    return date(year, month, 1)


def _count_orders_in_range(
    aggregated: dict[date, dict[str, Decimal | int]],
    start_date: date,
    end_date: date,
) -> int:
    total = 0
    current = start_date
    while current < end_date:
        total += int(aggregated.get(current, {}).get("order_count", 0))
        current = current.fromordinal(current.toordinal() + 1)
    return total


def _build_day_trend_points(
    start_date: date,
    total_days: int,
    scheduled: dict[date, dict[str, Decimal | int]],
    delivery: dict[date, dict[str, Decimal | int]],
) -> list[dict[str, int | str]]:
    points: list[dict[str, int | str]] = []
    for offset in range(total_days):
        current = start_date + timedelta(days=offset)
        points.append({
            "key": current.isoformat(),
            "label": current.strftime("%m-%d"),
            "scheduled_count": int(scheduled.get(current, {}).get("order_count", 0)),
            "delivery_count": int(delivery.get(current, {}).get("order_count", 0)),
        })
    return points


def _build_week_trend_points(
    start_date: date,
    total_weeks: int,
    scheduled: dict[date, dict[str, Decimal | int]],
    delivery: dict[date, dict[str, Decimal | int]],
) -> list[dict[str, int | str]]:
    points: list[dict[str, int | str]] = []
    for offset in range(total_weeks):
        bucket_start = start_date + timedelta(weeks=offset)
        bucket_end = bucket_start + timedelta(days=7)
        points.append({
            "key": bucket_start.isoformat(),
            "label": bucket_start.strftime("%m-%d"),
            "scheduled_count": _count_orders_in_range(scheduled, bucket_start, bucket_end),
            "delivery_count": _count_orders_in_range(delivery, bucket_start, bucket_end),
        })
    return points


def _build_month_trend_points(
    start_date: date,
    total_months: int,
    scheduled: dict[date, dict[str, Decimal | int]],
    delivery: dict[date, dict[str, Decimal | int]],
) -> list[dict[str, int | str]]:
    points: list[dict[str, int | str]] = []
    for offset in range(total_months):
        bucket_start = _shift_month(start_date, offset)
        bucket_end = _shift_month(bucket_start, 1)
        points.append({
            "key": bucket_start.strftime("%Y-%m"),
            "label": bucket_start.strftime("%Y-%m"),
            "scheduled_count": _count_orders_in_range(scheduled, bucket_start, bucket_end),
            "delivery_count": _count_orders_in_range(delivery, bucket_start, bucket_end),
        })
    return points
